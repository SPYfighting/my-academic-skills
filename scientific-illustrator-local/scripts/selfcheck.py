#!/usr/bin/env python3
"""Offline package checks. No Illustrator connection, network, or installation."""
import argparse
import ast
import csv
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SKILL = Path(__file__).resolve().parents[1]


def report(message):
    print(str(message).encode('ascii', 'backslashreplace').decode('ascii'))


def check_package():
    from PIL import Image, ImageDraw
    import numpy as np
    from figurelib.common import FigureError, read_json
    from figurelib.jobs import prepare, verify_job, vector_job
    from figurelib.svg import compile_svg
    from figurelib.text import erase_rows, cleanup_audit
    from figurelib.illustrator import draw

    def rejected(function):
        try:
            function()
        except FigureError:
            return
        raise AssertionError('Invalid input was accepted')

    for source in (SKILL / 'scripts').rglob('*.py'):
        ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
    report('ok  recursive Python syntax')

    fixture = SKILL / 'examples' / 'editable-workflow.svg'
    compiled = compile_svg(fixture)
    assert compiled['live_text_count'] == 5 and compiled['raster_count'] == 0
    with tempfile.TemporaryDirectory(prefix='scientific-vector-selfcheck-') as folder:
        temp = Path(folder)
        jobdir = temp / 'job'
        first = prepare(fixture, jobdir)
        assert prepare(fixture, jobdir)['job_id'] == first['job_id']
        assert verify_job(jobdir)['live_text_count'] == 5
        assert draw(jobdir, dry_run=True)['illustrator_untouched']
        report('ok  live-text fixture, stable preparation, and native-free dry run')

        cache = read_json(jobdir / 'geometry-cache.json')
        assert all(len({cache['atoms'][i]['kind'] for i in b['indices']}) == 1 for b in cache['batches'])
        (jobdir / 'figure_master.svg').write_text('<svg/>', encoding='utf-8')
        rejected(lambda: verify_job(jobdir))
        report('ok  changed source rejected; text batches retain paint order')

        for index, body in enumerate([
            '<image href="https://invalid.example/image.png" width="10" height="10"/>',
            '<script>alert(1)</script>',
            '<path d="M 0 0 Q broken"/>',
        ]):
            invalid = temp / ('invalid-%s.svg' % index)
            invalid.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">' + body + '</svg>', encoding='utf-8')
            rejected(lambda: compile_svg(invalid))
        report('ok  embedded image, script, and malformed path rejected')

        loop = temp / 'loop.svg'
        loop.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M0 0 C10 0 0 10 0 0Z"/></svg>', encoding='utf-8')
        curve = compile_svg(loop)['atoms'][0]['subpaths'][0]
        assert curve['closed'] and len(curve['points']) == 2
        assert curve['points'][1]['a'] == [3.75, 3.75]
        report('ok  closed single-cubic geometry preserved')

        background = np.repeat(np.arange(80, 120, dtype=np.uint8)[:, None, None], 60, axis=1)
        background = np.repeat(background, 3, axis=2)
        marked = background.copy(); marked[10:20, 10:30] = 0
        original, clean = temp / 'original.png', temp / 'clean.png'
        Image.fromarray(marked).save(original)
        manifest = {'canvas': [60, 40], 'runs': [{'id': 'label', 'text': 'Test', 'x': 10, 'y': 20,
            'font_size': 10, 'font_family': 'Arial', 'reviewed': True,
            'erase_bbox': [10, 10, 30, 20], 'background_sample_x': [5, 6]}]}
        erase_rows(original, clean, manifest, confirmed=True)
        assert np.array_equal(np.asarray(Image.open(clean)), background)
        assert cleanup_audit(original, clean, manifest)['outside_changed_pixel_fraction'] == 0
        rejected(lambda: erase_rows(original, original, manifest, confirmed=True))
        manifest['runs'][0]['background_sample_x'] = [12]
        rejected(lambda: erase_rows(original, temp / 'bad.png', manifest, confirmed=True))
        report('ok  row-gradient cleanup; original overwrite and contaminated samples rejected')

        raster = temp / 'shapes.png'
        im = Image.new('RGB', (60, 40), 'white')
        ImageDraw.Draw(im).rectangle((10, 8, 45, 32), fill='#66aacc'); im.save(raster)
        traced = vector_job(raster, temp / 'traced', 'contours', 'none')
        assert traced['total_atoms'] > 0
        comparison = temp / 'traced' / 'candidate_comparison.csv'
        with comparison.open(encoding='utf-8-sig', newline='') as handle:
            assert next(csv.reader(handle))[0] == 'candidate'
        assert b'<svg' in (temp / 'traced' / 'figure_master.svg').read_bytes()
        report('ok  local contour pipeline and English CSV output')

    node = shutil.which('node')
    if node:
        result = subprocess.run([node, '--check'], input=(SKILL / 'scripts' / 'illustrator_runtime.jsx').read_text(encoding='utf-8'),
                                text=True, encoding='utf-8', capture_output=True)
        assert result.returncode == 0, result.stderr
        report('ok  JSX syntax in Node (not a native Illustrator test)')
    else:
        report('SKIP  JSX syntax: Node is not available')

    powershell = shutil.which('powershell.exe') if os.name == 'nt' else None
    if powershell:
        path = str(SKILL / 'scripts' / 'bridge-windows.ps1').replace("'", "''")
        command = "$t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseFile('" + path + "',[ref]$t,[ref]$e)|Out-Null;if($e.Count){$e|Out-String|Write-Error;exit 1}"
        result = subprocess.run([powershell, '-NoProfile', '-Command', command], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        report('ok  Windows bridge syntax (no COM connection)')
    else:
        report('SKIP  Windows bridge parser: PowerShell 5.1 is not available')
    report('PASS  package checks; native application and visual acceptance remain separate')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.worker:
        local = SKILL / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        requested = os.environ.get('SCIENTIFIC_ILLUSTRATOR_PYTHON')
        selected = Path(requested).expanduser() if requested else (local if local.is_file() else Path(sys.executable))
        if requested and not selected.is_absolute():
            report('FAIL  SCIENTIFIC_ILLUSTRATOR_PYTHON must be an absolute path'); return 1
        if not selected.is_file():
            report('FAIL  SCIENTIFIC_ILLUSTRATOR_PYTHON does not identify an executable'); return 1
        if selected.resolve() != Path(sys.executable).resolve():
            return subprocess.run([str(selected), '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--worker'] +
                                  (['--verbose'] if args.verbose else [])).returncode
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        report('FAIL  use CPython 3.11-3.13; see references/installation-and-compatibility.md'); return 1
    try:
        check_package()
        return 0
    except Exception as exc:
        report('FAIL  ' + str(exc))
        if isinstance(exc, ImportError):
            report('Prepare scripts/setup_environment.py or set SCIENTIFIC_ILLUSTRATOR_PYTHON to a compatible environment')
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
