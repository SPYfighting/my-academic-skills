"""Recover real editable text without sending images to an external service."""
from __future__ import annotations
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageColor
from .common import FigureError, atomic_bytes, finite, digest, require_new_output
from .svg import NS, load_svg, canvas, compile_svg
ET.register_namespace('', NS)


def validate_manifest(manifest: dict, width: int, height: int) -> list[dict]:
    if not isinstance(manifest,dict):
        raise FigureError('Text manifest must be a JSON object')
    if manifest.get('canvas') != [width, height]:
        raise FigureError('Text manifest canvas must exactly match the image dimensions')
    runs = manifest.get('runs')
    if not isinstance(runs, list):
        raise FigureError('Text manifest requires a runs array (use [] only for truly text-free input)')
    ids=set()
    for run in runs:
        if not isinstance(run,dict) or not isinstance(run.get('text'),str):
            raise FigureError('Each text run must contain an explicit text string')
        if not isinstance(run.get('id'),str) or not run['id'] or run['id'] in ids:
            raise FigureError('Text runs require unique nonempty ids')
        ids.add(run['id'])
        for key in ('x','y','font_size'):
            if isinstance(run.get(key),bool) or not isinstance(run.get(key),(int,float)):
                raise FigureError(key+' must be a JSON number, not a string or boolean')
            finite(run.get(key),key)
        if run['font_size']<=0:
            raise FigureError('font_size must be positive')
        if not run.get('font_family'):
            raise FigureError('Supply font_family, and check it on the target machine')
        if run.get('reviewed') is not True:
            raise FigureError('Every text run must be reviewed against the original image')
        if '\n' in run['text'] or '\r' in run['text']:
            raise FigureError('Use one text run per line, with a baseline y')
        bbox=run.get('erase_bbox')
        if not isinstance(bbox,list) or len(bbox)!=4:
            raise FigureError('Each run requires erase_bbox [left, top, right, bottom]')
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) for x in bbox):
            raise FigureError('erase_bbox coordinates must be JSON numbers')
        x0,y0,x1,y1=[finite(x,'erase_bbox') for x in bbox]
        if not (0<=x0<x1<=width and 0<=y0<y1<=height):
            raise FigureError('erase_bbox must lie within the image')
        if run.get('anchor','start') not in ('start','middle','end'):
            raise FigureError('Invalid text anchor')
        if run.get('layer','top')!='top' and not run.get('insert_before'):
            raise FigureError('Non-top text needs insert_before pointing to a validated SVG id')
    return runs


def cleanup_audit(source: Path, cleaned: Path, manifest: dict, max_outside_mae: float=0.5) -> dict:
    a=np.asarray(Image.open(source).convert('RGB')); b=np.asarray(Image.open(cleaned).convert('RGB'))
    if a.shape!=b.shape:
        raise FigureError('Cleanup changed image dimensions; coordinates are no longer valid')
    h,w=a.shape[:2]; runs=validate_manifest(manifest,w,h)
    expected=manifest.get('source_sha256')
    if expected and expected!=digest(source):
        raise FigureError('Text manifest belongs to another source image')
    outside=np.ones((h,w),dtype=bool)
    for r in runs:
        x0,y0,x1,y1=[int(round(x)) for x in r['erase_bbox']]
        outside[y0:y1,x0:x1]=False
    if outside.mean()<0.5:
        raise FigureError('Text-erasure boxes cover >50% of the image; manually review / split the task')
    diff=np.abs(a.astype(np.float32)-b.astype(np.float32)).mean(2)
    mae=float(diff[outside].mean()) if outside.any() else 0.0
    altered=float((diff[outside]>8).mean()) if outside.any() else 0.0
    report={'outside_text_mae_0_255':mae,'outside_changed_pixel_fraction':altered,
            'threshold_mae':max_outside_mae,'passed':mae<=max_outside_mae and altered<=0.01,
            'limitation':'Checks pixels outside text boxes only; structures inside boxes still require visual review.'}
    if not report['passed']:
        raise FigureError(f'Cleanup altered non-text content (outside MAE={mae:.3f}, changed={altered:.3%}). Do not continue.')
    return report


def erase_flat(source: Path, output: Path, manifest: dict, confirmed: bool=False) -> None:
    if not confirmed:
        raise FigureError('Local erasure requires explicit confirmation that every rectangle contains only text and a uniform background')
    require_new_output(output, source)
    im=Image.open(source).convert('RGB'); runs=validate_manifest(manifest,*im.size)
    if manifest.get('source_sha256') and manifest['source_sha256']!=digest(source):
        raise FigureError('Manifest source hash mismatch')
    for r in runs:
        if not r.get('background'):
            raise FigureError('Local erasure needs the explicitly checked background color for each run')
        box=tuple(int(round(x)) for x in r['erase_bbox'])
        im.paste(ImageColor.getrgb(r['background']),box)
    import io
    stream=io.BytesIO(); im.save(stream,format='PNG'); atomic_bytes(output,stream.getvalue())


def merge_text(vector: Path, output: Path, manifest: dict, compile_result: bool=True) -> dict | None:
    require_new_output(output, vector)
    root=load_svg(vector); vb=canvas(root)
    if vb[:2]!=[0,0] or vb[2:]!=manifest.get('canvas'):
        raise FigureError('Text merge requires viewBox 0 0 width height matching the manifest')
    runs=validate_manifest(manifest,int(vb[2]),int(vb[3]))
    ids={e.get('id') for e in root.iter() if e.get('id')}
    for r in runs:
        if r['id'] in ids:
            raise FigureError('Text id collides with a vector object: '+r['id'])
        ids.add(r['id'])
        attrs={'id':r['id'],'x':str(r['x']),'y':str(r['y']),'font-family':r['font_family'],
               'font-size':str(r['font_size']),'fill':r.get('fill','#000000'),'text-anchor':r.get('anchor','start'),
               'font-weight':str(r.get('font_weight','normal')),'font-style':r.get('font_style','normal'),
               'opacity':str(r.get('opacity',1)),'letter-spacing':str(r.get('letter_spacing',0))}
        if r.get('rotation'):
            attrs['transform']=f'rotate({finite(r["rotation"])} {r["x"]} {r["y"]})'
        el=ET.Element('{'+NS+'}text',attrs); el.text=r['text']
        before=r.get('insert_before')
        if before:
            found=False
            for parent in root.iter():
                for i,child in enumerate(list(parent)):
                    if child.get('id')==before:
                        # Inserting into a transformed group would double-transform absolute coordinates.
                        if parent is not root:
                            raise FigureError('insert_before must target a root-level object; flatten groups first')
                        parent.insert(i,el); found=True; break
                if found: break
            if not found: raise FigureError('insert_before target not found: '+before)
        else:
            root.append(el)
    atomic_bytes(output,ET.tostring(root,encoding='utf-8',xml_declaration=True))
    return compile_svg(output) if compile_result else None


def erase_rows(source: Path, output: Path, manifest: dict, confirmed: bool=False) -> None:
    """Reconstruct a reviewed horizontally uniform background using same-row samples."""
    if not confirmed:
        raise FigureError('Row sampling needs reviewed text-only boxes and background sample columns')
    require_new_output(output,source)
    original=np.asarray(Image.open(source).convert('RGB'));h,w=original.shape[:2]
    runs=validate_manifest(manifest,w,h)
    if manifest.get('source_sha256') and manifest['source_sha256']!=digest(source):
        raise FigureError('Manifest source hash mismatch')
    result=original.copy()
    boxes=[tuple(int(round(x)) for x in r['erase_bbox']) for r in runs]
    for r,(x0,y0,x1,y1) in zip(runs,boxes):
        columns=r.get('background_sample_x')
        if not isinstance(columns,list) or not columns or any(type(x) is not int or not 0<=x<w for x in columns):
            raise FigureError('background_sample_x requires reviewed integer columns within the source image')
        for x in columns:
            if any(bx0<=x<bx1 and y0<by1 and y1>by0 for bx0,by0,bx1,by1 in boxes):
                raise FigureError('Background samples must not intersect any text-erasure box')
        rows=np.rint(np.median(original[y0:y1,columns,:],axis=1)).astype(np.uint8)
        result[y0:y1,x0:x1]=rows[:,None,:]
    import io
    stream=io.BytesIO();Image.fromarray(result).save(stream,format='PNG');atomic_bytes(output,stream.getvalue())
