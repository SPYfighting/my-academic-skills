"""Shared native playback. OS adapters transport trusted JSX, never input SVG code."""
from __future__ import annotations
import contextlib
import json
import math
import os
import platform
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from .common import FigureError, read_json, write_json
from .jobs import verify_job, prepare, utc

SCRIPTS = Path(__file__).resolve().parents[1]


def literal(value) -> str:
    # ASCII also escapes U+2028 / U+2029 for ExtendScript's ES3 parser.
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':'))


def apple_quote(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('\r', '\\r').replace('\n', '\\n') + '"'


def mac_script(app_path: str) -> str:
    # Compile against the actual running bundle, not a hardcoded year/version.
    app = apple_quote(app_path)
    return f'''on run argv
    if not (application {app} is running) then error "Illustrator is no longer running"
    set jsxFile to POSIX file (item 1 of argv)
    with timeout of 600 seconds
        tell application {app}
            return do javascript jsxFile
        end tell
    end timeout
end run
'''


class Bridge:
    """Attach only; one persistent COM host, or version-specific macOS bundle."""
    def __init__(self, app_path: str | None = None, prog_id: str | None = None):
        self.system = platform.system()
        self.process = None
        self.app_path = app_path
        self.prog_id = prog_id

    def __enter__(self):
        if self.system == 'Windows':
            if self.app_path:
                raise FigureError('--app-path is macOS-only; use --prog-id on Windows')
            args = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(SCRIPTS / 'bridge-windows.ps1')]
            if self.prog_id:
                args += ['-ProgId', self.prog_id]
            self.process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding='utf-8', bufsize=1,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.lines = queue.Queue()
            def reader():
                for line in self.process.stdout:
                    self.lines.put(line)
                self.lines.put(None)
            threading.Thread(target=reader, daemon=True).start()
        elif self.system == 'Darwin':
            if self.prog_id:
                raise FigureError('--prog-id is Windows-only')
            # NSWorkspace discovery does not launch apps or require System Events accessibility.
            script = '''ObjC.import('AppKit');
var apps = $.NSWorkspace.sharedWorkspace.runningApplications, out = [];
for (var i=0; i<apps.count; i++) {
 var a=apps.objectAtIndex(i), id=ObjC.unwrap(a.bundleIdentifier) || '';
 if (/^com\\.adobe\\.illustrator(?:\\.|$)/i.test(id))
  out.push({path:ObjC.unwrap(a.bundleURL.path),id:id});
}
JSON.stringify(out);'''
            result = subprocess.run(['/usr/bin/osascript', '-l', 'JavaScript', '-e', script],
                capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise FigureError('Cannot inspect running macOS applications: ' + result.stderr.strip())
            apps = json.loads(result.stdout)
            if self.app_path:
                apps = [a for a in apps if Path(a['path']).resolve() == Path(self.app_path).expanduser().resolve()]
            if len(apps) != 1:
                raise FigureError('Open one Illustrator instance, or select its exact running bundle with --app-path. Running: ' + literal(apps))
            self.app_path = apps[0]['path']
        else:
            raise FigureError('Native Illustrator requires Windows or macOS. SVG preparation works on this OS.')
        return self

    def execute(self, script: str) -> str:
        if self.system == 'Windows':
            if self.process.poll() is not None:
                raise FigureError('Illustrator COM bridge exited; open Illustrator in the same user session')
            self.process.stdin.write(literal({'script': script}) + '\n')
            self.process.stdin.flush()
            try:
                line = self.lines.get(timeout=610)
            except queue.Empty:
                raise FigureError('Illustrator did not respond. Check its dialogs; do not start another drawing until it is idle.')
            if line is None:
                raise FigureError('Illustrator COM bridge closed unexpectedly')
            try:
                data = json.loads(line.lstrip('\ufeff'))
            except ValueError as exc:
                raise FigureError('Invalid COM bridge response: ' + line[:500]) from exc
            if not data.get('ok'):
                raise FigureError(data.get('error', 'COM bridge failed'))
            return data['result']
        with tempfile.TemporaryDirectory(prefix='scientific-illustrator-') as directory:
            jsx = Path(directory) / 'invoke.jsx'
            jsx.write_text(script, encoding='utf-8')
            result = subprocess.run(
                ['/usr/bin/osascript', '-', str(jsx)], input=mac_script(self.app_path),
                capture_output=True, text=True, encoding='utf-8', timeout=610)
            if result.returncode:
                raise FigureError('macOS Illustrator automation failed. Check System Settings > Privacy & Security > Automation for your terminal/agent. ' + result.stderr.strip())
            return result.stdout.rstrip('\r\n')

    def __exit__(self, *args):
        if self.process:
            with contextlib.suppress(OSError):
                self.process.stdin.close()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
            self.process.stdout.close()


# ES3-safe encoder: native JSON is absent from some Illustrator versions.
ENCODER = r'''function enc(v){
 if(v===null)return 'null';
 if(typeof v==='string')return '"'+v.replace(/[\\"\x00-\x1f\u2028\u2029]/g,function(ch){var h=ch.charCodeAt(0).toString(16);return '\\u'+('0000'+h).slice(-4);})+'"';
 if(typeof v==='number'||typeof v==='boolean')return String(v);
 var a=[],k;if(v instanceof Array){for(k=0;k<v.length;k++)a.push(enc(v[k]));return '['+a.join(',')+']';}
 for(k in v)if(v.hasOwnProperty(k))a.push(enc(k)+':'+enc(v[k]));return '{'+a.join(',')+'}';
}'''


def probe(bridge: Bridge) -> dict:
    script = '(function(){' + ENCODER + r'''
var d=app.documents.length?app.activeDocument:null,p='';
if(d)try{p=d.fullName.fsName;}catch(e){}
return enc({version:String(app.version),os:String($.os),documents:app.documents.length,
 documentName:d?d.name:'',documentPath:p,pageItems:d?d.pageItems.length:0,
 capabilities:{path:!!d&&!!d.pathItems,text:!!d&&!!d.textFrames,
 artboards:!!d&&!!d.artboards,saveAs:!!d&&typeof d.saveAs!=='undefined',
 png:typeof ExportOptionsPNG24!=='undefined'},
 artboardRect:d?d.artboards[d.artboards.getActiveArtboardIndex()].artboardRect:null});}());'''
    return json.loads(bridge.execute(script))


@contextlib.contextmanager
def writer_lock():
    # OS advisory lock auto-releases after a crashed agent; file presence isn't a lock.
    path = Path(tempfile.gettempdir()) / 'scientific-illustrator-local-writer.lock'
    with path.open('a+b') as handle:
        handle.seek(0)
        if path.stat().st_size == 0:
            handle.write(b'0'); handle.flush(); handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise FigureError('Another local Illustrator drawing is running') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def same_path(a: str, b: str, system: str | None = None) -> bool:
    # Preserve case on macOS, which may use a case-sensitive volume.
    if (system or platform.system()) == 'Windows':
        return a.replace('\\', '/').casefold() == b.replace('\\', '/').casefold()
    return a == b


def draw(directory: Path, reviewed=False, dry_run=False, allow_overlap=False,
         width=0.72, height=0.78, checkpoint=30, app_path=None, prog_id=None,
         bridge=None, _locked=False) -> dict:
    if not all(math.isfinite(v) and .05 <= v <= 1 for v in (width, height)) or not 1 <= checkpoint <= 3600:
        raise FigureError('Invalid placement fractions or checkpoint interval')
    directory = directory.resolve(); job = verify_job(directory)
    cache = read_json(directory / 'geometry-cache.json')
    if dry_run:
        return {'dry_run': True, 'illustrator_untouched': True, 'objects': job['total_atoms'], 'batches': job['batches']}
    if not reviewed:
        raise FigureError('Review source, text, and candidates, then pass --approve-review')
    for name in ('figure.ai', 'figure.png', 'playback.json'):
        if (directory / name).is_symlink():
            raise FigureError('Native output paths must not be symlinks')
    state_path = directory / 'playback.json'
    prior = read_json(state_path) if state_path.exists() else None
    output_ai, output_png = directory / 'figure.ai', directory / 'figure.png'
    if not prior and (output_ai.exists() or output_png.exists()):
        raise FigureError('Unowned native output already exists; use a new job directory')
    if prior and (prior.get('job_id') != job['job_id'] or prior.get('cache_sha256') != job['cache_sha256']):
        raise FigureError('Playback state belongs to different geometry')
    with (contextlib.nullcontext() if _locked else writer_lock()), (contextlib.nullcontext(bridge) if bridge else Bridge(app_path, prog_id)) as host:
        info = probe(host)
        if not info['documents'] or not all(info['capabilities'].values()):
            raise FigureError('Open a document; this Illustrator must support native paths, live text, artboards, AI save and PNG export')
        if prior:
            expected = prior.get('document_path', '')
            if expected and not same_path(info['documentPath'], expected):
                raise FigureError('Activate the original target document / saved figure.ai before resuming')
            if not expected and info['documentName'] != prior.get('document_name'):
                raise FigureError('Activate the original target document before resuming')
        kinds = [a['kind'] for a in cache['atoms']]
        first_text = kinds.index('text') if 'text' in kinds else len(kinds)
        text_on_top = 'path' not in kinds[first_text:] and all(
            len({cache['atoms'][i]['kind'] for i in b['indices']}) == 1 for b in cache['batches'])
        base = dict(documentName=info['documentName'], documentPath=info['documentPath'],
            cacheHash=job['cache_sha256'], rootName='svl_' + job['job_id'], viewBox=cache['view_box'],
            maxWidthFraction=width, maxHeightFraction=height, allowOverlap=allow_overlap,
            resumeOutput=bool(prior), textOnTop=text_on_top, windows=platform.system() == 'Windows')
        def invoke(operation, **extra):
            cfg = dict(base, operation=operation, **extra)
            result = host.execute('var SCIENTIFIC_VECTOR_CONFIG=' + literal(cfg) +
                '; $.evalFile(new File(' + literal(str(SCRIPTS / 'illustrator_runtime.jsx')) + '));')
            if not result.startswith('OK|'):
                raise FigureError('Illustrator stopped: ' + result)
            return result
        def state(status, count, **extra):
            write_json(state_path, dict(schema_version='1.1', job_id=job['job_id'], cache_sha256=job['cache_sha256'],
                status=status, completed_batches=count, document_name=base['documentName'],
                document_path=base['documentPath'], illustrator_version=info['version'], system=platform.system(),
                updated_utc=utc(), text_on_top=text_on_top, **extra))
        def save(count):
            result = invoke('save', outputAi=str(output_ai))
            base.update(documentName=result.split('|documentName=', 1)[1], documentPath=str(output_ai), resumeOutput=True)
            state('drawing', count)
        completed = 0
        try:
            invoke('begin', fontAtoms=[a for a in cache['atoms'] if a['kind'] == 'text'])
            state('drawing', completed)
            last_save = 0.0; last_progress = 0.0
            batches = []
            for batch in cache['batches']:
                atoms = [cache['atoms'][i] for i in batch['indices']]
                invoke('batch', batchName=batch['name'], atoms=atoms)
                batches.append(dict(name=batch['name'], atoms=atoms))
                completed += 1
                state('drawing', completed)
                if time.monotonic() - last_save >= checkpoint:
                    save(completed); last_save = time.monotonic()
                if time.monotonic() - last_progress >= 10:
                    print(f'Illustrator: {completed}/{len(cache["batches"])} batches', file=sys.stderr, flush=True)
                    last_progress = time.monotonic()
            invoke('verify', batches=batches)
            audit = invoke('audit')
            text_match=re.search(r'\|live_text=(\d+)\|',audit)
            if not text_match or int(text_match.group(1))!=job['live_text_count']:
                raise FigureError('Native live-text count differs from the reviewed SVG: '+audit)
            save(completed)
            invoke('export', outputPng=str(output_png))
            if not output_ai.is_file() or not output_png.is_file() or min(output_ai.stat().st_size, output_png.stat().st_size) == 0:
                raise FigureError('Native AI / PNG output is missing or empty')
            result = dict(ai=str(output_ai), png=str(output_png), native_audit=audit,
                          illustrator_version=info['version'], visual_review_required=True, text_on_top=text_on_top)
            state('native_export_complete_visual_review_required', completed, native_audit=audit)
            return result
        except Exception as exc:
            # Preserve valid state for recovery; completed native batches are still verified on replay.
            if state_path.exists():
                state('interrupted', completed, error=str(exc))
            raise


def native_test(directory: Path, create_document=False, confirm_empty=False, app_path=None, prog_id=None) -> dict:
    if not (create_document or confirm_empty):
        raise FigureError('Use --create-document for a new disposable document, or --confirm-empty-document for the active empty document')
    directory = directory.resolve()
    prepare(SCRIPTS.parent / 'examples' / 'editable-workflow.svg', directory)
    with writer_lock(), Bridge(app_path, prog_id) as host:
        if create_document:
            host.execute('app.documents.add(DocumentColorSpace.RGB,600,400); "CREATED_DISPOSABLE";')
        info = probe(host)
        if not info['documents'] or info['pageItems']:
            raise FigureError('Native test requires a completely empty disposable document')
        sentinel = host.execute('''(function(){var d=app.activeDocument,b=d.artboards[0].artboardRect;
var p=d.pathItems.rectangle(b[1]-2,b[0]+2,3,3);p.name='scientific-local-sentinel';
p.note='must-stay-unchanged';return 'OK';}());''')
        if sentinel != 'OK':
            raise FigureError('Cannot create native preservation sentinel')
        result = draw(directory, reviewed=True, bridge=host, _locked=True)
        before = int(host.execute('app.activeDocument.pageItems.length;'))
        draw(directory, reviewed=True, bridge=host, _locked=True)
        after = int(host.execute('app.activeDocument.pageItems.length;'))
        check = host.execute('''(function(){var d=app.activeDocument,s=null,t=null;
for(var i=0;i<d.pageItems.length;i++)if(d.pageItems[i].name==='scientific-local-sentinel')s=d.pageItems[i];
for(var j=0;j<d.textFrames.length;j++)if(d.textFrames[j].name==='input_label')t=d.textFrames[j];
if(!s||s.note!=='must-stay-unchanged'||!t||t.contents!=='Input')return 'ERROR';
t.contents='Editable';if(t.contents!=='Editable')return 'ERROR';t.contents='Input';
return 'OK';}());''')
        if before != after or check != 'OK':
            raise FigureError('Native replay, sentinel preservation or live-text editing failed')
        result.update(status='AUTOMATED_NATIVE_CHECKS_PASS_VISUAL_REVIEW_REQUIRED',
            objects_before_replay=before, objects_after_replay=after, system=platform.system(), updated_utc=utc())
        write_json(directory / 'native-audit.json', result)
        return result


def native_trace(image: Path, output: Path, colors=32, authorized=False, app_path=None, prog_id=None):
    from .common import require_new_output, atomic_bytes
    from PIL import Image
    if not authorized:
        raise FigureError('Native Image Trace requires explicit temporary-document authorization')
    require_new_output(output,image)
    if output.suffix.lower()!='.svg' or not image.is_file() or not 2<=colors<=256:
        raise FigureError('Native trace needs an existing image, new .svg output and 2–256 colors')
    # Do not let an SVG or another script-bearing document bypass our SVG validator.
    with Image.open(image) as raster:
        if raster.width*raster.height>8_000_000 or raster.getexif().get(274,1)!=1:
            raise FigureError('Native trace requires a raster of at most 8 megapixels with normalized orientation')
        raster.load()
    output.parent.mkdir(parents=True,exist_ok=True)
    payload=literal(dict(input=str(image.resolve()),output=str(output.resolve()),colors=colors))
    script='(function(){var c='+payload+r''',original=app.documents.length?app.activeDocument:null,temp=null;
try {
 temp=app.documents.add(DocumentColorSpace.RGB);
 var item=temp.placedItems.add();item.file=new File(c.input);app.redraw();
 var plugin=item.trace(),trace=plugin.tracing;
 trace.tracingOptions.tracingMode=TracingModeType.TRACINGMODECOLOR;
 trace.tracingOptions.maxColors=c.colors;trace.tracingOptions.ignoreWhite=false;
 trace.tracingOptions.pathFitting=0.5;trace.tracingOptions.minArea=1;app.redraw();
 var expanded=trace.expandTracing();temp.artboards[0].artboardRect=expanded.visibleBounds;
 var options=new ExportOptionsSVG();options.cssProperties=SVGCSSPropertyLocation.PRESENTATIONATTRIBUTES;
 options.documentEncoding=SVGDocumentEncoding.UTF8;options.embedRasterImages=false;
 temp.exportFile(new File(c.output),ExportType.SVG,options);return 'OK|NATIVE_TRACE_EXPORTED|version='+app.version;
}catch(e){return 'ERROR|'+String(e);}
finally {if(temp)try{temp.close(SaveOptions.DONOTSAVECHANGES);}catch(ignore){}
 if(original)try{original.activate();}catch(ignoreActive){}}
}());'''
    with writer_lock(), Bridge(app_path,prog_id) as host:
        response=host.execute(script)
    if not response.startswith('OK|') or not output.is_file():
        raise FigureError('Native Image Trace failed: '+response)
    raw=output.read_text(encoding='utf-8-sig')
    if re.search(r'<!ENTITY|<!DOCTYPE[^>]*\[',raw,re.I):
        raise FigureError('Unexpected entity or internal DTD in native SVG')
    raw=re.sub(r'<!DOCTYPE\s+svg\s+PUBLIC\s+"[^"]*"\s+"[^"]*"\s*>','',raw,flags=re.I)
    atomic_bytes(output,raw.encode('utf-8'))
    return {'engine':'illustrator-image-trace','native_response':response,'colors':colors,
        'temporary_document_authorized':True,'degraded_backend':False,'review_required':True}
