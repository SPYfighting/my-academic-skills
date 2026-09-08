"""Local trace backends. No network. Official VTracer 1.x CLI, 1.x/0.6 Python,
plus a tested OpenCV contour fallback with explicitly recorded provenance."""
from __future__ import annotations
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from PIL import Image
from .common import FigureError, atomic_bytes
from .svg import NS, compile_svg, load_svg, canvas
from .preview import render_paths, quality
ET.register_namespace('', NS)


def cli_binary() -> str | None:
    custom=os.environ.get('SCIENTIFIC_VECTOR_VTRACER')
    if custom:
        p=Path(custom)
        if not p.is_absolute() or not p.is_file():
            raise FigureError('SCIENTIFIC_VECTOR_VTRACER must name an existing absolute executable path')
        return str(p)
    vendor=Path(__file__).resolve().parents[2]/'bin'/('vtracer.exe' if os.name=='nt' else 'vtracer')
    return str(vendor) if vendor.is_file() else shutil.which('vtracer')


def available() -> list[str]:
    result=[]
    if cli_binary(): result.append('vtracer-cli')
    if importlib.util.find_spec('vtracer'): result.append('vtracer-python')
    return result+['contours']


def normalize_svg(path: Path) -> None:
    root=load_svg(path); vb=canvas(root); root.set('viewBox',' '.join(str(x) for x in vb))
    used={x.get('id') for x in root.iter() if x.get('id')}
    n=0
    for el in root.iter():
        if el.tag.rsplit('}',1)[-1] in {'path','rect','circle','ellipse','line','polygon','polyline'} and not el.get('id'):
            n+=1
            eid=f'trace_{n:06d}'
            while eid in used:
                n+=1; eid=f'trace_{n:06d}'
            el.set('id',eid); used.add(eid)
    atomic_bytes(path,ET.tostring(root,encoding='utf-8',xml_declaration=True))


def contour_trace(image: Path, output: Path, colors: int=24, tolerance: float=0.5) -> dict:
    im=Image.open(image).convert('RGB')
    if im.width*im.height>8_000_000:
        raise FigureError('Contour fallback limited to 8 megapixels; use VTracer for larger images')
    quant=im.quantize(colors=colors,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    labels=np.asarray(quant); palette=np.asarray(quant.getpalette(),dtype=np.uint8).reshape(-1,3)
    unique,counts=np.unique(labels,return_counts=True)
    # Full background covers the canvas. Foreground regions are then drawn over it.
    bg=int(unique[np.argmax(counts)]); width,height=im.size
    root=ET.Element('{'+NS+'}svg',{'viewBox':f'0 0 {width} {height}','width':str(width),'height':str(height)})
    ET.SubElement(root,'{'+NS+'}rect',{'id':'background','x':'0','y':'0','width':str(width),'height':str(height),
                 'fill':'#'+''.join(f'{x:02x}' for x in palette[bg])})
    counter=0
    for label in unique:
        if int(label)==bg: continue
        mask=(labels==label).astype(np.uint8)*255
        # Upsampling before contouring prevents one-pixel lines from becoming zero-area paths.
        doubled=cv2.resize(mask,None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST)
        contours,hierarchy=cv2.findContours(doubled,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None: continue
        for index,contour in enumerate(contours):
            if hierarchy[0,index,3]!=-1: continue
            parts=[contour]; child=int(hierarchy[0,index,2])
            while child!=-1:
                parts.append(contours[child]); child=int(hierarchy[0,child,0])
            commands=[]
            for part in parts:
                poly=cv2.approxPolyDP(part,max(tolerance*2,0.01),True).reshape(-1,2).astype(float)/2
                if len(poly)<3:
                    poly=part.reshape(-1,2).astype(float)/2
                if len(poly)<3: continue
                commands.append('M '+' L '.join(f'{x:.3f} {y:.3f}' for x,y in poly)+' Z')
            if not commands: continue
            counter+=1
            ET.SubElement(root,'{'+NS+'}path',{'id':f'contour_{counter:06d}','fill-rule':'evenodd',
                'fill':'#'+''.join(f'{x:02x}' for x in palette[int(label)]),'d':' '.join(commands)})
    atomic_bytes(output,ET.tostring(root,encoding='utf-8',xml_declaration=True))
    return {'engine':'opencv-contours','version':cv2.__version__,'colors':colors,'tolerance_px':tolerance,
            'degraded_backend':True,'limitation':'Polygonal contours, not VTracer splines; visual / editability review required.'}


def trace_once(image: Path, output: Path, backend: str, detail: str) -> dict:
    if detail=='faithful' and backend!='vtracer-cli':
        raise FigureError('The faithful profile requires the pinned VTracer 1.x CLI; no silent contour fallback')
    if backend=='contours':
        return contour_trace(image,output,colors=32 if detail=='fine' else 16,tolerance=0.18 if detail=='fine' else 0.55)
    if backend=='illustrator':
        from .illustrator import native_trace
        meta=native_trace(image,output,32 if detail=='fine' else 16,authorized=True)
        normalize_svg(output)
        return dict(meta,detail=detail)
    if backend=='vtracer-cli':
        exe=cli_binary()
        if not exe: raise FigureError('VTracer CLI is not installed')
        version=subprocess.run([exe,'--version'],check=True,capture_output=True,text=True,timeout=15).stdout.strip()
        if '1.0' not in version:
            raise FigureError('This CLI adapter requires VTracer 1.x; do not pass 1.x flags to a 0.6 executable')
        args=[exe,str(image.resolve()),str(output.resolve()),'--filter-speckle','0','--hierarchical','cutout',
              '--max-colors','32' if detail=='fine' else '16','--simplify','0.4' if detail=='fine' else '1.0']
        scaled=None
        if detail=='faithful':
            with Image.open(image) as src:
                original_size=src.size
                if src.width*src.height*16>32_000_000:
                    raise FigureError('4x faithful tracing is limited to 32 megapixels after resampling; use a smaller input or another profile')
                scaled=output.with_suffix('.trace-input.png')
                src.convert('RGB').resize((src.width*4,src.height*4),Image.Resampling.LANCZOS).save(scaled)
            args=[exe,str(scaled.resolve()),str(output.resolve()),'--hierarchical','cutout','--mode','spline',
                '--filter-speckle','4','--color-precision','8','--gradient-step','4','--simplify','0.6',
                '--max-colors','128','--optimize','0']
        try:
            p=subprocess.run(args,capture_output=True,text=True,timeout=300)
        finally:
            if scaled is not None: scaled.unlink(missing_ok=True)
        if p.returncode: raise FigureError('VTracer CLI failed: '+p.stderr[-1200:])
        if detail=='faithful':
            root=load_svg(output)
            contents=list(root)
            for child in contents: root.remove(child)
            g=ET.SubElement(root,'{'+NS+'}g',{'id':'trace_geometry','transform':'scale(0.25)'})
            g.extend(contents)
            w,h=original_size
            root.set('viewBox',f'0 0 {w} {h}');root.set('width',str(w));root.set('height',str(h))
            atomic_bytes(output,ET.tostring(root,encoding='utf-8',xml_declaration=True))
        normalize_svg(output)
        return {'engine':'vtracer-cli','version':version,'detail':detail,'degraded_backend':False,
                'trace_arguments':args[3:],'resampling_scale':4 if detail=='faithful' else 1,
                'resampling_note':'Interpolation smooths fitting; it does not recover missing image information.' if detail=='faithful' else None}
    if backend=='vtracer-python':
        import vtracer
        from importlib.metadata import version
        # The two published Python APIs are intentionally distinct.
        if hasattr(vtracer,'Config'):
            cfg=vtracer.Config(mode='spline' if detail=='fine' else 'polygon',hierarchical='cutout')
            cfg.convert_file(str(image),str(output))
        elif hasattr(vtracer,'convert_image_to_svg_py'):
            vtracer.convert_image_to_svg_py(str(image),str(output),colormode='color',hierarchical='stacked',mode='spline',
                filter_speckle=0,color_precision=7 if detail=='fine' else 6,layer_difference=8 if detail=='fine' else 16,
                corner_threshold=60,length_threshold=4.0,max_iterations=10,splice_threshold=45,path_precision=3)
        else: raise FigureError('Unsupported installed VTracer Python API')
        normalize_svg(output)
        return {'engine':'vtracer-python','version':version('vtracer'),'detail':detail,'degraded_backend':False}
    raise FigureError('Unknown backend: '+backend)


def rank_candidates(image: Path, directory: Path, backend: str='auto', regions: list[dict] | None=None, include_illustrator: bool=False, profile: str='auto') -> dict:
    reference=Image.open(image).convert('RGB')
    if reference.width*reference.height>8_000_000:
        raise FigureError('Ranking is limited to 8 megapixels; resize explicitly and update text coordinates')
    directory.mkdir(parents=True,exist_ok=True)
    engines=available() if backend=='auto' else [backend]
    if profile not in ('auto','balanced','fine','faithful'): raise FigureError('Unknown fidelity profile')
    if profile=='faithful':
        if backend not in ('auto','vtracer-cli') or not cli_binary():
            raise FigureError('Faithful tracing requires the installed VTracer 1.x CLI')
        engines=['vtracer-cli']
    if include_illustrator:
        engines.append('illustrator')
    # Avoid silently duplicating the same VTracer engine when both interfaces exist.
    if backend=='auto' and 'vtracer-cli' in engines and 'vtracer-python' in engines:
        engines.remove('vtracer-python')
    results=[]; errors=[]
    for engine in engines:
        for detail in (('balanced','fine') if profile=='auto' else (profile,)):
            file=directory/f'{engine}_{detail}.svg'
            try:
                meta=trace_once(image,file,engine,detail)
                cache=compile_svg(file)
                rendered=render_paths(cache,reference.size)
                rendered.save(file.with_suffix('.png'))
                qa=quality(reference,rendered,regions)
                # Favor fidelity; only break nearly equal scores with editability complexity.
                complexity=min(cache['total_points']/100000,1)*0.004
                results.append({'svg':file.name,'png':file.with_suffix('.png').name,'backend':meta,'qa':qa,
                                'path_objects':cache['total_atoms'],'anchors':cache['total_points'],
                                'selection_score':qa['ranking_score']-complexity})
            except Exception as exc:
                if isinstance(exc,(KeyboardInterrupt,SystemExit)): raise
                errors.append({'engine':engine,'detail':detail,'error':str(exc)})
    if not results: raise FigureError('No candidate completed: '+str(errors))
    best=max(results,key=lambda x:(x['qa']['heuristic_pass'],x['selection_score']))
    return {'selected':best,'candidates':results,'failed_candidates':errors,
            'review_required':True,'note':'Metrics rank raster fidelity, not biology, semantic grouping, or editable-object quality.'}
