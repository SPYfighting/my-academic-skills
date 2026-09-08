"""Strict SVG subset -> Illustrator-ready cubic geometry.

Adapted in part from Cell-lct's public geometry-cache design and point conversion
(yrui-cmd, MIT, commit 4af98d8057f48a944141f9122da7aba83d544d28).
Unsupported effects are rejected, never silently dropped. This is not a full SVG renderer.
"""
from __future__ import annotations
import math
import re
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET
from defusedxml import ElementTree as SafeET
from fontTools.misc.transform import Transform
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path
from PIL import ImageColor
from .common import FigureError, finite

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
NUMBER = r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?'
NUM = re.compile(NUMBER)
TRANS = re.compile(r'([A-Za-z]+)\s*\(([^)]*)\)')
SHAPES = {'path', 'rect', 'circle', 'ellipse', 'line', 'polygon', 'polyline'}
TAGS = SHAPES | {'svg', 'g', 'text', 'title', 'desc', 'metadata', 'defs'}
PRESENT = {'fill', 'stroke', 'stroke-width', 'fill-rule', 'fill-opacity', 'stroke-opacity', 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'stroke-dasharray', 'stroke-dashoffset', 'color', 'font-family', 'font-size', 'font-weight', 'font-style', 'text-anchor', 'letter-spacing', 'dominant-baseline', 'visibility'}
DEFAULT = {'fill':'black', 'stroke':'none', 'stroke-width':'1', 'fill-rule':'nonzero', 'fill-opacity':'1', 'stroke-opacity':'1', 'stroke-linecap':'butt', 'stroke-linejoin':'miter', 'stroke-miterlimit':'4', 'stroke-dasharray':'none', 'stroke-dashoffset':'0', 'color':'black', 'font-family':'Arial', 'font-size':'16', 'font-weight':'normal', 'font-style':'normal', 'text-anchor':'start', 'letter-spacing':'0', 'dominant-baseline':'alphabetic', 'visibility':'visible'}


def name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def number(value: str | float | None, default: float = 0) -> float:
    if value is None:
        return float(default)
    # Numeric user units / px only. Reject %/pt/mm rather than treating them as px.
    raw = str(value).strip()
    if not re.fullmatch(NUMBER + r'(?:px)?', raw):
        raise FigureError(f'Unsupported SVG length {raw!r}; normalize to numeric user units / px')
    return finite(raw[:-2] if raw.endswith('px') else raw)


def numbers(value: str) -> list[float]:
    stripped = NUM.sub('', value)
    if stripped.strip(' ,\t\r\n'):
        raise FigureError('Invalid numeric list: ' + value[:100])
    return [finite(v) for v in NUM.findall(value)]


def transform(raw: str | None) -> Transform:
    result = Transform()
    if not raw:
        return result
    pos = 0
    for match in TRANS.finditer(raw):
        if raw[pos:match.start()].strip(' ,\t\r\n'):
            raise FigureError('Malformed transform')
        key, values = match.group(1).lower(), numbers(match.group(2))
        if key == 'matrix' and len(values) == 6:
            op = Transform(*values)
        elif key == 'translate' and len(values) in (1, 2):
            op = Transform().translate(values[0], values[1] if len(values) == 2 else 0)
        elif key == 'scale' and len(values) in (1, 2):
            op = Transform().scale(values[0], values[1] if len(values) == 2 else values[0])
        elif key == 'rotate' and len(values) in (1, 3):
            op = Transform().rotate(math.radians(values[0]))
            if len(values) == 3:
                op = Transform().translate(*values[1:]).transform(op).translate(-values[1], -values[2])
        elif key == 'skewx' and len(values) == 1:
            op = Transform(1, 0, math.tan(math.radians(values[0])), 1, 0, 0)
        elif key == 'skewy' and len(values) == 1:
            op = Transform(1, math.tan(math.radians(values[0])), 0, 1, 0, 0)
        else:
            raise FigureError('Unsupported transform: ' + match.group(0))
        result = result.transform(op)
        pos = match.end()
    if raw[pos:].strip(' ,\t\r\n'):
        raise FigureError('Malformed transform')
    for v in result:
        finite(v, 'transform')
    if abs(result.xx * result.yy - result.xy * result.yx) < 1e-12:
        raise FigureError('Singular transform is not drawable')
    return result


def load_svg(path: Path) -> ET.Element:
    data = Path(path).read_bytes()
    if len(data) > 30_000_000:
        raise FigureError('SVG exceeds the 30 MB safety limit')
    # Even harmless DTDs are unnecessary in this restricted format.
    if re.search(br'<!\s*(?:DOCTYPE|ENTITY)', data, re.I):
        raise FigureError('DOCTYPE / ENTITY declarations are not allowed')
    try:
        root = SafeET.fromstring(data)
    except Exception as exc:
        raise FigureError('Unsafe or malformed SVG: ' + str(exc)) from exc
    if name(root.tag) != 'svg':
        raise FigureError('Root must be <svg>')
    if root.tag.startswith('{') and not root.tag.startswith('{' + NS + '}'):
        raise FigureError('Unexpected root namespace')
    ids: set[str] = set()
    for i, el in enumerate(root.iter()):
        if i > 100_000:
            raise FigureError('SVG exceeds element count limit')
        tag = name(el.tag)
        if tag not in TAGS:
            raise FigureError(f'Unsupported <{tag}>. Expand effects to plain paths first.')
        if el is not root and tag == 'svg':
            raise FigureError('Nested SVG viewports must be flattened first')
        if tag == 'defs' and len(el):
            raise FigureError('Definitions / reusable resources must be expanded')
        if tag == 'text' and len(el):
            raise FigureError('Split <tspan>/multiline text into separate <text> elements')
        eid = el.get('id')
        if eid:
            if eid in ids:
                raise FigureError('Duplicate SVG id: ' + eid)
            ids.add(eid)
        for k, v in el.attrib.items():
            lk, lv = name(k).lower(), v.lower()
            if lk.startswith('on') or lk in {'href', 'src', 'base'} or 'url(' in lv or '@import' in lv or 'expression(' in lv:
                raise FigureError(f'Active content / external resource blocked: {lk}')
            if lk in {'filter', 'mask', 'clip-path', 'marker-start', 'marker-mid', 'marker-end'} and lv not in {'none', ''}:
                raise FigureError(f'{lk} must be expanded before import')
            if lk == 'class':
                raise FigureError('Class-dependent CSS must be inlined')
            if lk == 'vector-effect' and lv not in {'none', ''}:
                raise FigureError('Non-scaling strokes must be expanded first')
            if lk in {'paint-order', 'mix-blend-mode'} and lv not in {'normal', ''}:
                raise FigureError('Unsupported paint order / blend mode')
    return root


def canvas(root: ET.Element) -> list[float]:
    if root.get('viewBox'):
        vb = numbers(root.get('viewBox', ''))
    else:
        vb = [0.0, 0.0, number(root.get('width')), number(root.get('height'))]
    if len(vb) != 4 or vb[2] <= 0 or vb[3] <= 0:
        raise FigureError('A positive finite viewBox or width / height is required')
    return vb


def style_of(el: ET.Element, parent: dict[str, str]) -> dict[str, str]:
    st = parent.copy()
    for key in PRESENT:
        if el.get(key) is not None:
            st[key] = el.get(key, '')
    for statement in el.get('style', '').split(';'):
        if not statement.strip():
            continue
        if ':' not in statement:
            raise FigureError('Malformed inline style')
        key, value = [x.strip() for x in statement.split(':', 1)]
        if key not in PRESENT | {'opacity', 'display'}:
            raise FigureError('Unsupported inline style property: ' + key)
        st[key] = value
    st['opacity'] = el.get('opacity', st.get('opacity', '1'))
    st['display'] = el.get('display', st.get('display', 'inline'))
    return st


def color(raw: str, current: str) -> list[int] | None:
    if raw == 'none':
        return None
    try:
        rgba = ImageColor.getcolor(current if raw == 'currentColor' else raw, 'RGBA')
    except ValueError as exc:
        raise FigureError('Unsupported color: ' + raw) from exc
    if rgba[3] != 255:
        raise FigureError('Use fill-opacity / stroke-opacity instead of alpha-bearing color')
    return list(rgba[:3])


def shape_path(el: ET.Element) -> str:
    tag = name(el.tag)
    n = lambda k, d=0: number(el.get(k), d)
    if tag == 'path':
        value = re.sub(r'\s+', ' ', el.get('d', '').strip())
        if not value:
            raise FigureError('Empty path')
        return value
    if tag == 'line':
        return f'M {n("x1")} {n("y1")} L {n("x2")} {n("y2")}'
    if tag in {'polygon', 'polyline'}:
        p = numbers(el.get('points', ''))
        if len(p) < 4 or len(p) % 2:
            raise FigureError('Malformed polygon / polyline')
        return 'M ' + ' L '.join(f'{p[i]} {p[i+1]}' for i in range(0, len(p), 2)) + (' Z' if tag == 'polygon' else '')
    if tag == 'rect':
        x,y,w,h = n('x'),n('y'),n('width'),n('height')
        if min(w,h) <= 0:
            raise FigureError('Rectangle dimensions must be positive')
        rx = min(n('rx', n('ry')), w/2)
        ry = min(n('ry', rx), h/2)
        if min(rx,ry) < 0:
            raise FigureError('Negative corner radius')
        if rx == 0 or ry == 0:
            return f'M {x} {y} H {x+w} V {y+h} H {x} Z'
        return f'M {x+rx} {y} H {x+w-rx} A {rx} {ry} 0 0 1 {x+w} {y+ry} V {y+h-ry} A {rx} {ry} 0 0 1 {x+w-rx} {y+h} H {x+rx} A {rx} {ry} 0 0 1 {x} {y+h-ry} V {y+ry} A {rx} {ry} 0 0 1 {x+rx} {y} Z'
    if tag in {'circle','ellipse'}:
        x,y = n('cx'),n('cy')
        rx = n('r') if tag == 'circle' else n('rx')
        ry = rx if tag == 'circle' else n('ry')
        if min(rx,ry) <= 0:
            raise FigureError('Circle / ellipse radii must be positive')
        return f'M {x+rx} {y} A {rx} {ry} 0 1 1 {x-rx} {y} A {rx} {ry} 0 1 1 {x+rx} {y} Z'
    raise FigureError('Unknown shape')


def subpaths(data: str, matrix: Transform) -> list[dict[str, Any]]:
    # Cubic anchors / handles follow Cell-lct's representation. Quadratics and arcs
    # are converted once by fontTools, not approximated again in Illustrator.
    recording = RecordingPen()
    try:
        parse_path(data, Qu2CuPen(TransformPen(recording, matrix), max_err=0.02, all_cubic=True))
    except Exception as exc:
        raise FigureError('Cannot parse path: ' + str(exc)) from exc
    out: list[dict[str, Any]] = []
    pts: list[dict[str, Any]] = []
    def point(p):
        q = [round(finite(x, 'path coordinate'), 6) for x in p]
        return {'a':q[:], 'l':q[:], 'r':q[:]}
    def flush(closed):
        nonlocal pts
        if closed and len(pts)>1 and all(abs(a-b)<1e-6 for a,b in zip(pts[0]['a'],pts[-1]['a'])):
            pts[0]['l'] = pts.pop()['l']
        if closed and len(pts)==1 and (pts[0]['l']!=pts[0]['a'] or pts[0]['r']!=pts[0]['a']):
            # A single cubic can form a visible closed loop. Split at t=0.5
            # by de Casteljau so Illustrator receives two distinct anchors.
            p=pts[0]
            def midpoint(a,b):return [(x+y)/2 for x,y in zip(a,b)]
            q1=midpoint(p['a'],p['r']);q2=midpoint(p['r'],p['l']);q3=midpoint(p['l'],p['a'])
            left=midpoint(q1,q2);right=midpoint(q2,q3)
            p['r']=q1;p['l']=q3
            pts.append({'a':midpoint(left,right),'l':left,'r':right})
        if len(pts)>=2:
            out.append({'closed':closed,'points':pts})
        pts=[]
    for op, args in recording.value:
        if op=='moveTo':
            flush(False); pts=[point(args[0])]
        elif op=='lineTo':
            for p in args:
                pts.append(point(p))
        elif op=='curveTo':
            if not pts or len(args)%3:
                raise FigureError('Malformed cubic')
            for j in range(0,len(args),3):
                pts[-1]['r']=point(args[j])['a']; q=point(args[j+2]); q['l']=point(args[j+1])['a']; pts.append(q)
        elif op=='closePath':
            flush(True)
        elif op=='endPath':
            flush(False)
        else:
            raise FigureError('Unsupported path operation: '+op)
    flush(False)
    if not out:
        raise FigureError('Path has no drawable contour')
    return out


def compile_svg(path: Path, max_points: int = 1_000_000) -> dict[str, Any]:
    root=load_svg(path); vb=canvas(root); atoms=[]; atom_names=set(); point_count=0
    def visit(el: ET.Element, parent: dict[str,str], matrix: Transform, depth: int=0):
        nonlocal point_count
        if depth>64:
            raise FigureError('SVG nesting exceeds 64')
        tag=name(el.tag)
        if tag in {'title','desc','metadata','defs'}:
            return
        st=style_of(el,parent)
        if st['display']=='none' or st['visibility']=='hidden':
            return
        if st['display']!='inline' or st['visibility']!='visible':
            raise FigureError('Unsupported display / visibility')
        m=matrix.transform(transform(el.get('transform')))
        opacity=number(st['opacity'])
        if not 0<=opacity<=1:
            raise FigureError('Opacity must be in [0,1]')
        if tag in {'svg','g'}:
            if opacity!=1:
                raise FigureError('Group opacity must be expanded; child multiplication is not equivalent')
            st.pop('opacity',None); st.pop('display',None)
            for child in el: visit(child,st,m,depth+1)
            return
        fill=color(st['fill'],st['color']); stroke=color(st['stroke'],st['color'])
        fill_opacity=number(st['fill-opacity'])*opacity; stroke_opacity=number(st['stroke-opacity'])*opacity
        if not all(0<=v<=1 for v in [fill_opacity,stroke_opacity]):
            raise FigureError('Paint opacity must be in [0,1]')
        # Separate fill/stroke alpha is not faithfully representable on one native
        # PathItem. Reject nonmatching alpha instead of changing appearance.
        if fill is not None and stroke is not None and abs(fill_opacity-stroke_opacity)>1e-8:
            raise FigureError('Separate fill/stroke opacity must be split into two SVG objects')
        sx=math.hypot(m.xx,m.xy); sy=math.hypot(m.yx,m.yy)
        if (stroke is not None or tag=='text') and (abs(sx-sy)>1e-6 or abs(m.xx*m.yx+m.xy*m.yy)>1e-6):
            raise FigureError('Anisotropic/skewed text or stroke requires expansion to paths')
        atom={'name':el.get('id') or f'object_{len(atoms)+1:05d}', 'fill':fill,'stroke':stroke,
              'opacity':100*(fill_opacity if fill is not None else stroke_opacity), 'fill_rule':st['fill-rule'],
              'stroke_width':number(st['stroke-width'])*sx, 'linecap':st['stroke-linecap'],
              'linejoin':st['stroke-linejoin'], 'miter':number(st['stroke-miterlimit']),
              'dashes':[] if st['stroke-dasharray']=='none' else [x*sx for x in numbers(st['stroke-dasharray'])],
              'dash_offset':number(st['stroke-dashoffset'])*sx}
        if atom['fill_rule'] not in {'nonzero','evenodd'} or atom['linecap'] not in {'butt','round','square'} or atom['linejoin'] not in {'miter','round','bevel'}:
            raise FigureError('Unsupported fill rule / line style')
        if atom['stroke_width']<0 or any(x<0 for x in atom['dashes']):
            raise FigureError('Negative stroke width / dash')
        if tag=='text':
            if fill is None:
                raise FigureError('Live text requires an explicit visible fill; no silent black substitution')
            if stroke is not None:
                raise FigureError('Stroked text is not supported; retain fill-only live text')
            if st['dominant-baseline'] not in {'alphabetic','auto'}:
                raise FigureError('Text baseline must be alphabetic; supply baseline y')
            if '\n' in (el.text or '') or '\r' in (el.text or ''):
                raise FigureError('Split multiline text into individual baseline-positioned runs')
            if m.xx*m.yy-m.xy*m.yx<=0:
                raise FigureError('Reflected text is not supported')
            size=number(st['font-size'])*sx
            if size<=0: raise FigureError('Text size must be positive')
            if st['text-anchor'] not in {'start','middle','end'}: raise FigureError('Invalid text anchor')
            atom.update({'kind':'text','text':el.text or '', 'position':list(m.transformPoint((number(el.get('x')),number(el.get('y'))))),
                         'font_family':st['font-family'].strip('"\''), 'font_weight':st['font-weight'], 'font_style':st['font-style'],
                         'font_size':size, 'anchor':st['text-anchor'], 'rotation':math.degrees(math.atan2(m.xy,m.xx)),
                         'letter_spacing':number(st['letter-spacing'])*sx})
        else:
            paths=subpaths(shape_path(el),m)
            count=sum(len(p['points']) for p in paths); point_count+=count
            if point_count>max_points: raise FigureError('Vector exceeds anchor count limit')
            atom.update({'kind':'path','subpaths':paths,'point_count':count})
        if len(atoms)>=50_000: raise FigureError('Too many editable objects (>50,000)')
        if atom['name'] in atom_names:
            raise FigureError('Object-name collision; provide explicit unique SVG ids')
        atom_names.add(atom['name'])
        atoms.append(atom)
    visit(root,DEFAULT,Transform())
    if not atoms: raise FigureError('SVG contains no drawable objects')
    return {'schema_version':'1.0','view_box':vb,'atoms':atoms,'total_atoms':len(atoms),'total_points':point_count,
            'live_text_count':sum(a['kind']=='text' for a in atoms),'raster_count':0}
