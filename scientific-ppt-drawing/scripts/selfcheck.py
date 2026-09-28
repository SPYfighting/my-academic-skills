#!/usr/bin/env python3
"""Offline SVG-to-native-PPTX checks; no PowerPoint or network required."""
from __future__ import annotations

import ast
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

from figurelib.common import FigureError
from figurelib.powerpoint import compatibility_report, render
from figurelib.svg import compile_svg
from figure_cli import inspect

SKILL = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run() -> None:
    for source in (SKILL / 'scripts').rglob('*.py'):
        ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
    print('ok  Python syntax')

    with tempfile.TemporaryDirectory(prefix='scientific-ppt-selfcheck-') as directory:
        temp = Path(directory)
        svg = SKILL / 'examples' / 'compatibility-smoke.svg'
        compiled = compile_svg(svg)
        require(compiled['total_atoms'] == 3 and compiled['live_text_count'] == 1,
                'Valid SVG did not retain three editable objects')
        pptx = temp / 'sample.pptx'
        audit = render(svg, pptx, width_in=4, fallback_font='Arial')
        counts = inspect(pptx)
        profile = compatibility_report(pptx)
        require(counts['native_shapes'] == 3 and counts['editable_text_shapes'] == 1,
                'Native shape or text count changed')
        require(counts['cubic_segments'] > 0 and counts['picture_shapes'] == 0,
                'Curve became a picture or lost its cubic geometry')
        require(audit['font_substitutions'] == 1 and audit['fallback_font'] == 'Arial',
                'Font fallback was not recorded')
        require(profile['core_markup_profile'] and profile['live_text_shapes'] == 1,
                'Generated PPTX is outside the base native-shape profile')
        with ZipFile(pptx) as deck:
            slide = deck.read('ppt/slides/slide1.xml')
            require(b'typeface="Arial"' in slide, 'Fallback font is absent from native text')
        print('ok  native paths and live text; base PPTX profile; font fallback')

        bad_svg = temp / 'embedded.svg'
        bad_svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">'
                           '<image href="https://invalid.example/x.png" width="10" height="10"/>'
                           '</svg>', encoding='utf-8')
        try:
            compile_svg(bad_svg)
        except FigureError:
            pass
        else:
            raise AssertionError('Embedded image was accepted')

        extended = temp / 'extended.pptx'
        with ZipFile(pptx) as src, ZipFile(extended, 'x', compression=ZIP_DEFLATED) as dst:
            for entry in src.infolist():
                data = src.read(entry.filename)
                if entry.filename == 'ppt/slides/slide1.xml':
                    root = ET.fromstring(data)
                    ET.SubElement(root, '{http://schemas.microsoft.com/office/powerpoint/2010/main}creationId', val='1')
                    data = ET.tostring(root, encoding='utf-8', xml_declaration=True)
                dst.writestr(entry, data)
        require(not compatibility_report(extended)['core_markup_profile'],
                'Office-version extension was not detected')
        print('ok  embedded raster rejected; newer markup detected')

    print('PASS  offline checks; target PowerPoint rendering and editing remain untested')


if __name__ == '__main__':
    run()
