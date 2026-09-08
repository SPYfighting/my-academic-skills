"""Local geometry preview for raster-trace ranking; NOT a publication renderer.

Uses OpenCV supersampling for filled paths. Supports no text / dash fidelity claims.
The authoritative full-document preview is exported by Illustrator.
"""
from __future__ import annotations
import math
import cv2
import numpy as np
from PIL import Image
from .common import FigureError


def sample_path(subpath: dict, scale: float=1.0) -> np.ndarray:
    points=subpath['points']; out=[points[0]['a']]
    count=len(points) if subpath['closed'] else len(points)-1
    for i in range(count):
        p=points[i]; q=points[(i+1)%len(points)]
        a,b,c,d=[np.array(v,dtype=float) for v in [p['a'],p['r'],q['l'],q['a']]]
        distance=np.linalg.norm(a-b)+np.linalg.norm(b-c)+np.linalg.norm(c-d)
        steps=min(256,max(2,int(math.ceil(distance*scale/2))))
        if np.allclose(a,b) and np.allclose(c,d):
            out.append(d.tolist()); continue
        for t in np.linspace(0,1,steps+1)[1:]:
            out.append(((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d).tolist())
    return np.asarray(out,dtype=float)


def render_paths(cache: dict, size: tuple[int,int] | None=None, supersample: int=2) -> Image.Image:
    vx,vy,vw,vh=cache['view_box']; width,height=size or (round(vw),round(vh))
    if width<1 or height<1 or width*height*supersample**2>40_000_000:
        raise FigureError('Preview dimensions exceed safety limits')
    sx=width/vw*supersample; sy=height/vh*supersample
    im=np.full((height*supersample,width*supersample,3),255,np.uint8)
    for atom in cache['atoms']:
        if atom['kind']=='text':
            raise FigureError('The local ranking renderer intentionally excludes text. Use Illustrator for the final text preview.')
        contours=[]
        for sub in atom['subpaths']:
            pts=sample_path(sub,max(sx,sy)); pts[:,0]=(pts[:,0]-vx)*sx; pts[:,1]=(pts[:,1]-vy)*sy
            contours.append(np.rint(pts).astype(np.int32).reshape(-1,1,2))
        layer=im.copy()
        if atom['fill'] is not None:
            # OpenCV fillPoly uses even-odd for compound contours. For nonzero
            # simple paths this is equivalent. Reject ambiguous compound nonzero.
            if len(contours)>1 and atom['fill_rule']=='nonzero':
                # VTracer's compound contours normally alternate orientation;
                # arbitrary same-winding overlaps require an external renderer.
                areas=[cv2.contourArea(c,oriented=True) for c in contours]
                if len({1 if a>0 else -1 for a in areas if a})<2:
                    raise FigureError('Ambiguous nonzero compound fill cannot be ranked by this preview renderer')
            cv2.fillPoly(layer,contours,tuple(atom['fill']),lineType=cv2.LINE_AA)
        if atom['stroke'] is not None:
            if atom['dashes']:
                raise FigureError('Dashed strokes require the Illustrator final preview')
            for contour,sub in zip(contours,atom['subpaths']):
                cv2.polylines(layer,[contour],sub['closed'],tuple(atom['stroke']),max(1,round(atom['stroke_width']*sx)),cv2.LINE_AA)
        opacity=atom['opacity']/100
        im=np.rint(im*(1-opacity)+layer*opacity).astype(np.uint8)
    return Image.fromarray(im).resize((width,height),Image.Resampling.LANCZOS)


def quality(reference: Image.Image, candidate: Image.Image, regions: list[dict] | None=None, renderer: str='local OpenCV geometry preview, not Illustrator') -> dict:
    a=np.asarray(reference.convert('RGB'),dtype=np.float32); b=np.asarray(candidate.convert('RGB'),dtype=np.float32)
    if a.shape!=b.shape: raise FigureError('QA images have different dimensions')
    diff=np.abs(a-b).mean(2)/255
    foreground=np.min(a,axis=2)<245
    fg_mae=float(diff[foreground].mean()) if foreground.any() else float(diff.mean())
    a8=a.astype(np.uint8); b8=b.astype(np.uint8)
    ea=cv2.Canny(cv2.cvtColor(a8,cv2.COLOR_RGB2GRAY),60,160)>0
    eb=cv2.Canny(cv2.cvtColor(b8,cv2.COLOR_RGB2GRAY),60,160)>0
    kernel=np.ones((3,3),np.uint8)
    da=cv2.dilate(ea.astype(np.uint8),kernel)>0; db=cv2.dilate(eb.astype(np.uint8),kernel)>0
    recall=float((ea&db).sum()/max(ea.sum(),1)); precision=float((eb&da).sum()/max(eb.sum(),1))
    if not ea.any() and not eb.any(): precision=recall=1.0
    edge_f1=2*precision*recall/max(precision+recall,1e-9)
    roi=[]
    h,w=diff.shape
    for reg in regions or []:
        x0,y0,x1,y1=map(int,reg['bbox'])
        if not (0<=x0<x1<=w and 0<=y0<y1<=h): raise FigureError('QA region outside image')
        value=float(diff[y0:y1,x0:x1].mean()); limit=float(reg.get('max_mae',0.08))
        roi.append({'name':reg['name'],'mae':value,'limit':limit,'passed':value<=limit})
    mae=float(diff.mean()); mse=float(np.mean((a-b)**2))
    psnr=None if mse==0 else 10*math.log10(255**2/mse)
    score=0.5*(1-fg_mae)+0.3*edge_f1+0.2*(1-mae)
    passed=mae<=0.06 and fg_mae<=0.12 and edge_f1>=0.65 and all(r['passed'] for r in roi)
    return {'mae':mae,'foreground_mae':fg_mae,'edge_f1_tolerance_1px':edge_f1,'psnr_db':psnr,
            'ranking_score':score,'regions':roi,'heuristic_pass':passed,
            'not_a_scientific_validation':True,'renderer':renderer}
