"""Render the reviewed SVG subset as native, editable PowerPoint shapes.

The source SVG parser is adapted from scientific-illustrator-local (MIT). This
module maps its cubic geometry and live text to DrawingML in a one-slide PPTX.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
import re
from pathlib import Path
from PIL import ImageFont

from .common import FigureError, digest, require_new_output, write_json
from .svg import compile_svg

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
ET.register_namespace('p', P)
ET.register_namespace('a', A)
EMU_PER_INCH = 914400


def q(ns: str, tag: str) -> str:
    return f'{{{ns}}}{tag}'


def sub(parent: ET.Element, ns: str, tag: str, **attrs: object) -> ET.Element:
    return ET.SubElement(parent, q(ns, tag), {k: str(v) for k, v in attrs.items()})


def rgb(parent: ET.Element, color: list[int], opacity: float) -> None:
    solid = sub(parent, A, 'solidFill')
    color_el = sub(solid, A, 'srgbClr', val=''.join(f'{v:02X}' for v in color))
    if opacity < 100:
        sub(color_el, A, 'alpha', val=round(opacity * 1000))


def shape_base(tree: ET.Element, ident: int, name: str) -> tuple[ET.Element, ET.Element]:
    shape = sub(tree, P, 'sp')
    nonvisual = sub(shape, P, 'nvSpPr')
    sub(nonvisual, P, 'cNvPr', id=ident, name=name)
    sub(nonvisual, P, 'cNvSpPr')
    sub(nonvisual, P, 'nvPr')
    return shape, sub(shape, P, 'spPr')


def local_point(point: list[float], min_x: float, min_y: float, scale: float) -> dict[str, str]:
    return {'x': str(round((point[0] - min_x) * scale)),
            'y': str(round((point[1] - min_y) * scale))}


def geometry_bounds(atom: dict) -> tuple[float, float, float, float]:
    coordinates = [point[handle] for contour in atom['subpaths'] for point in contour['points']
                   for handle in ('a', 'l', 'r')]
    return (min(p[0] for p in coordinates), min(p[1] for p in coordinates),
            max(p[0] for p in coordinates), max(p[1] for p in coordinates))


def path_shape(tree: ET.Element, atom: dict, ident: int, vb: list[float], scale: float) -> None:
    min_x, min_y, max_x, max_y = geometry_bounds(atom)
    if max_x - min_x <= 0 or max_y - min_y <= 0:
        # DrawingML requires a nonzero path viewport even for a straight line.
        max_x = max(max_x, min_x + 0.001)
        max_y = max(max_y, min_y + 0.001)
    shape, properties = shape_base(tree, ident, atom['name'])
    xfrm = sub(properties, A, 'xfrm')
    sub(xfrm, A, 'off', x=round((min_x - vb[0]) * scale), y=round((min_y - vb[1]) * scale))
    width = max(1, round((max_x - min_x) * scale))
    height = max(1, round((max_y - min_y) * scale))
    sub(xfrm, A, 'ext', cx=width, cy=height)
    custom = sub(properties, A, 'custGeom')
    sub(custom, A, 'avLst')
    paths = sub(custom, A, 'pathLst')
    for contour in atom['subpaths']:
        path = sub(paths, A, 'path', w=width, h=height)
        points = contour['points']
        move = sub(path, A, 'moveTo')
        sub(move, A, 'pt', **local_point(points[0]['a'], min_x, min_y, scale))
        pairs = list(zip(points, points[1:]))
        if contour['closed']:
            pairs.append((points[-1], points[0]))
        for start, end in pairs:
            straight = start['r'] == start['a'] and end['l'] == end['a']
            if straight:
                line = sub(path, A, 'lnTo')
                sub(line, A, 'pt', **local_point(end['a'], min_x, min_y, scale))
            else:
                curve = sub(path, A, 'cubicBezTo')
                for point in (start['r'], end['l'], end['a']):
                    sub(curve, A, 'pt', **local_point(point, min_x, min_y, scale))
        if contour['closed']:
            sub(path, A, 'close')
    if atom['fill'] is None:
        sub(properties, A, 'noFill')
    else:
        rgb(properties, atom['fill'], atom['opacity'])
    if atom['stroke'] is not None and atom['stroke_width'] > 0:
        line = sub(properties, A, 'ln', w=max(1, round(atom['stroke_width'] * scale)))
        rgb(line, atom['stroke'], atom['opacity'])
        if atom['linecap'] == 'round':
            line.set('cap', 'rnd')
        elif atom['linecap'] == 'square':
            line.set('cap', 'sq')
        if atom['linejoin'] == 'round':
            sub(line, A, 'round')
        elif atom['linejoin'] == 'bevel':
            sub(line, A, 'bevel')
        else:
            sub(line, A, 'miter', lim=max(1, round(atom['miter'] * 100000)))
    else:
        line = sub(properties, A, 'ln')
        sub(line, A, 'noFill')


def text_shape(tree: ET.Element, atom: dict, ident: int, vb: list[float], scale: float,
               fallback_font: str | None = None) -> None:
    text = atom['text']
    if not text:
        return
    size = atom['font_size']
    font_family = fallback_font or atom['font_family']
    # The box is intentionally generous and inset-free; PowerPoint remains the
    # authority on final font metrics, so visual review is still required.
    try:
        font = ImageFont.truetype(font_family, max(1, round(size)))
        measured_width = float(font.getlength(text))
    except (OSError, ValueError):
        measured_width = len(text) * size * 0.55
    estimated_width = max(size, measured_width + size * 0.5)
    box_height = size * 1.2
    x, baseline = atom['position']
    if atom['anchor'] == 'middle':
        x -= estimated_width / 2
    elif atom['anchor'] == 'end':
        x -= estimated_width
    top = baseline - size * 0.88
    shape, properties = shape_base(tree, ident, atom['name'])
    xfrm = sub(properties, A, 'xfrm')
    if atom['rotation']:
        xfrm.set('rot', str(round(atom['rotation'] * 60000)))
    sub(xfrm, A, 'off', x=round((x - vb[0]) * scale), y=round((top - vb[1]) * scale))
    sub(xfrm, A, 'ext', cx=max(1, round(estimated_width * scale)),
        cy=max(1, round(box_height * scale)))
    geom = sub(properties, A, 'prstGeom', prst='rect')
    sub(geom, A, 'avLst')
    sub(properties, A, 'noFill')
    line = sub(properties, A, 'ln')
    sub(line, A, 'noFill')
    body = sub(shape, P, 'txBody')
    sub(body, A, 'bodyPr', wrap='none', lIns='0', tIns='0', rIns='0', bIns='0', anchor='t')
    sub(body, A, 'lstStyle')
    paragraph = sub(body, A, 'p')
    sub(paragraph, A, 'pPr', algn={'start': 'l', 'middle': 'ctr', 'end': 'r'}[atom['anchor']])
    run = sub(paragraph, A, 'r')
    style = sub(run, A, 'rPr', lang='en-US', sz=max(100, round(size * 75)))
    if str(atom['font_weight']).lower() in ('bold', '700', '800', '900'):
        style.set('b', '1')
    if atom['font_style'] == 'italic':
        style.set('i', '1')
    rgb(style, atom['fill'], atom['opacity'])
    sub(style, A, 'latin', typeface=font_family)
    content = sub(run, A, 't')
    content.text = text
    if text != text.strip():
        content.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    sub(paragraph, A, 'endParaRPr', lang='en-US')


def render(svg: Path, output: Path, width_in: float | None = None,
           fallback_font: str | None = None) -> dict:
    svg, output = Path(svg), Path(output)
    require_new_output(output, svg)
    cache = compile_svg(svg)
    if fallback_font is not None and (not fallback_font.strip() or any(c in fallback_font for c in '<>\x00')):
        raise FigureError('Fallback font must be a nonempty font-family name')
    for atom in cache['atoms']:
        if atom['kind'] == 'path' and (atom['dashes'] or atom['dash_offset']):
            raise FigureError('Dashed SVG strokes must be expanded to native paths before rendering')
        if atom['kind'] == 'text' and atom['letter_spacing']:
            raise FigureError('SVG letter-spacing is not supported for live PowerPoint text')
    vb = cache['view_box']
    if width_in is None:
        width_in = vb[2] / 96
    if not 1 <= width_in <= 56:
        raise FigureError('Slide width must be 1-56 inches')
    height_in = width_in * vb[3] / vb[2]
    if not 1 <= height_in <= 56:
        raise FigureError('Slide height must be 1-56 inches')
    width_emu = round(width_in * EMU_PER_INCH)
    height_emu = round(height_in * EMU_PER_INCH)
    scale = width_emu / vb[2]
    template = Path(__file__).resolve().parents[2] / 'assets' / 'blank-native.pptx'
    with zipfile.ZipFile(template) as source:
        slide = ET.fromstring(source.read('ppt/slides/slide1.xml'))
        presentation = ET.fromstring(source.read('ppt/presentation.xml'))
        tree = slide.find(f'{q(P, "cSld")}/{q(P, "spTree")}')
        if tree is None:
            raise FigureError('Blank template lacks a shape tree')
        for child in list(tree):
            if child.tag not in (q(P, 'nvGrpSpPr'), q(P, 'grpSpPr')):
                tree.remove(child)
        for ident, atom in enumerate(cache['atoms'], start=2):
            if atom['kind'] == 'path':
                path_shape(tree, atom, ident, vb, scale)
            else:
                text_shape(tree, atom, ident, vb, scale, fallback_font)
        size = presentation.find(q(P, 'sldSz'))
        if size is None:
            raise FigureError('Blank template lacks slide size')
        size.set('cx', str(width_emu))
        size.set('cy', str(height_emu))
        replacements = {
            'ppt/slides/slide1.xml': ET.tostring(slide, encoding='utf-8', xml_declaration=True),
            'ppt/presentation.xml': ET.tostring(presentation, encoding='utf-8', xml_declaration=True),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as dest:
            for entry in source.infolist():
                dest.writestr(entry, replacements.get(entry.filename, source.read(entry.filename)))
    audit = {
        'source_svg': str(svg.resolve()), 'source_sha256': digest(svg),
        'pptx': str(output.resolve()), 'pptx_sha256': digest(output),
        'slide_inches': [round(width_in, 6), round(height_in, 6)],
        'path_shapes': sum(a['kind'] == 'path' for a in cache['atoms']),
        'live_text_shapes': sum(a['kind'] == 'text' and bool(a['text']) for a in cache['atoms']),
        'raster_shapes': 0,
        'fallback_font': fallback_font,
        'font_substitutions': sum(a['kind'] == 'text' and bool(a['text']) and
                                  a['font_family'] != fallback_font for a in cache['atoms'])
                              if fallback_font else 0,
        'limitations': ['Native PowerPoint appearance and point editing require visual review in PowerPoint.'],
    }
    write_json(output.with_suffix('.audit.json'), audit)
    return audit


def compatibility_report(pptx: Path) -> dict:
    """Check this renderer's conservative PPTX profile, not native app behavior."""
    versioned = re.compile(rb'http://schemas\.microsoft\.com/office/[^"<> ]+/20\d\d/')
    newer_parts, external_parts, media_parts, macro_parts = [], [], [], []
    pictures = graphics = native_shapes = live_text = 0
    with zipfile.ZipFile(pptx) as deck:
        for name in deck.namelist():
            if name.startswith('ppt/media/'):
                media_parts.append(name)
            if 'vbaProject' in name:
                macro_parts.append(name)
            if not name.endswith(('.xml', '.rels')):
                continue
            data = deck.read(name)
            if versioned.search(data):
                newer_parts.append(name)
            if name.endswith('.rels'):
                root = ET.fromstring(data)
                if any(el.get('TargetMode') == 'External' for el in root):
                    external_parts.append(name)
            elif name.startswith('ppt/slides/slide') and name.endswith('.xml'):
                root = ET.fromstring(data)
                pictures += len(root.findall(f'.//{q(P, "pic")}'))
                graphics += len(root.findall(f'.//{q(P, "graphicFrame")}'))
                shapes = root.findall(f'.//{q(P, "sp")}')
                native_shapes += len(shapes)
                live_text += sum(bool(shape.findall(f'.//{q(A, "t")}')) for shape in shapes)
    findings = {
        'versioned_extension_parts': newer_parts,
        'external_relationship_parts': external_parts,
        'media_parts': media_parts,
        'macro_parts': macro_parts,
        'picture_shapes': pictures,
        'graphic_frames': graphics,
    }
    return {
        'pptx': str(Path(pptx).resolve()),
        'core_markup_profile': not any(findings.values()),
        'native_shapes': native_shapes,
        'live_text_shapes': live_text,
        **findings,
        'boundary': 'Structural check only; open and edit in the target PowerPoint version to verify behavior.',
    }
