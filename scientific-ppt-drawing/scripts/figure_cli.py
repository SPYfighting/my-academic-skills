#!/usr/bin/env python3
"""Create native editable PowerPoint figures from reviewed SVG artwork."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

from figurelib.common import FigureError, read_json, require_new_output, write_json
from figurelib.powerpoint import compatibility_report, render
from figurelib.svg import compile_svg


def doctor() -> dict:
    packages = {}
    for name in ('Pillow', 'numpy', 'opencv-python-headless', 'fonttools', 'defusedxml'):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    from figurelib.trace import available
    template = Path(__file__).resolve().parents[1] / 'assets' / 'blank-native.pptx'
    return {'platform': platform.platform(), 'python': sys.version.split()[0],
            'packages': packages, 'trace_backends': available(),
            'blank_template_exists': template.is_file(),
            'powerpoint_ui_check': 'Open the generated PPTX in PowerPoint and inspect shapes and text.'}


def inspect(pptx: Path) -> dict:
    ns = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
          'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
    with zipfile.ZipFile(pptx) as deck:
        slides = sorted(n for n in deck.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml'))
        if not slides:
            raise FigureError('PPTX contains no slide XML')
        shapes = texts = curves = images = 0
        labels = []
        for name in slides:
            root = ET.fromstring(deck.read(name))
            shapes += len(root.findall('.//p:sp', ns))
            images += len(root.findall('.//p:pic', ns))
            curves += len(root.findall('.//a:cubicBezTo', ns))
            for shape in root.findall('.//p:sp', ns):
                runs = shape.findall('.//a:t', ns)
                if runs:
                    texts += 1
                    labels.append(''.join(el.text or '' for el in runs))
    return {'pptx': str(pptx.resolve()), 'slides': len(slides), 'native_shapes': shapes,
            'editable_text_shapes': texts, 'cubic_segments': curves,
            'picture_shapes': images, 'texts': labels}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor', help='Report local prerequisites and tracing backends')
    validate = commands.add_parser('validate', help='Check the supported SVG subset')
    validate.add_argument('svg', type=Path)
    output = commands.add_parser('render', help='Write a new native editable PPTX')
    output.add_argument('svg', type=Path)
    output.add_argument('pptx', type=Path)
    output.add_argument('--width-in', type=float)
    output.add_argument('--fallback-font', help='Replace live-text fonts in a new output, e.g. Arial')
    check = commands.add_parser('inspect', help='Count editable objects in a PPTX')
    check.add_argument('pptx', type=Path)
    compatibility = commands.add_parser('compatibility', help='Check conservative native PPTX markup')
    compatibility.add_argument('pptx', type=Path)
    trace = commands.add_parser('trace', help='Produce vector candidates from a raster reference')
    trace.add_argument('image', type=Path)
    trace.add_argument('directory', type=Path)
    trace.add_argument('--backend', choices=('auto', 'vtracer-cli', 'vtracer-python', 'contours'), default='auto')
    trace.add_argument('--profile', choices=('auto', 'balanced', 'fine', 'faithful'), default='auto')
    trace.add_argument('--regions', type=Path, help='Optional JSON file with {"regions": [...]}')
    merge = commands.add_parser('merge-text', help='Add reviewed live text to a vector SVG')
    merge.add_argument('svg', type=Path)
    merge.add_argument('manifest', type=Path)
    merge.add_argument('output', type=Path)
    erase = commands.add_parser('erase-flat-text', help='Erase reviewed text boxes over flat backgrounds')
    erase.add_argument('image', type=Path)
    erase.add_argument('manifest', type=Path)
    erase.add_argument('output', type=Path)
    erase.add_argument('--reviewed', action='store_true', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'doctor':
            result = doctor()
        elif args.command == 'validate':
            cache = compile_svg(args.svg)
            result = {key: cache[key] for key in ('view_box', 'total_atoms', 'total_points', 'live_text_count', 'raster_count')}
        elif args.command == 'render':
            result = render(args.svg, args.pptx, args.width_in, args.fallback_font)
            result['object_inspection'] = inspect(args.pptx)
        elif args.command == 'inspect':
            result = inspect(args.pptx)
        elif args.command == 'compatibility':
            result = compatibility_report(args.pptx)
        elif args.command == 'trace':
            from figurelib.trace import rank_candidates
            from figurelib.common import digest
            if args.directory.exists() and any(args.directory.iterdir()):
                raise FigureError('Trace output directory must be empty')
            regions = read_json(args.regions).get('regions', []) if args.regions else None
            result = rank_candidates(args.image, args.directory, args.backend, regions, args.profile)
            result['reference_image'] = str(args.image.resolve())
            result['reference_sha256'] = digest(args.image)
            write_json(args.directory / 'trace-review.json', result)
        elif args.command == 'merge-text':
            from figurelib.text import merge_text
            manifest = read_json(args.manifest)
            cache = merge_text(args.svg, args.output, manifest)
            result = {'svg': str(args.output.resolve()), 'live_text_count': cache['live_text_count']}
        else:
            from figurelib.text import erase_flat
            erase_flat(args.image, args.output, read_json(args.manifest), confirmed=args.reviewed)
            result = {'cleaned_image': str(args.output.resolve())}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == 'compatibility' and not result['core_markup_profile']:
            raise SystemExit(2)
    except (FigureError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == '__main__':
    main()
