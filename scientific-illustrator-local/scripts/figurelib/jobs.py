from __future__ import annotations
import csv
import io
import json
import platform
import uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageOps
from . import __version__
from .common import FigureError, digest, atomic_bytes, write_json, read_json
from .svg import compile_svg
from .trace import rank_candidates
from .text import merge_text, cleanup_audit


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def make_batches(atoms: list[dict], max_objects: int=40, max_points: int=2200) -> list[dict]:
    if not 1<=max_objects<=50 or max_points<100:
        raise FigureError('Invalid batch limits')
    batches=[]; current=[]; points=0
    for index,atom in enumerate(atoms):
        amount=atom.get('point_count',1)
        if current and (len(current)>=max_objects or points+amount>max_points or atoms[current[-1]]['kind']!=atom['kind']):
            batches.append({'indices':current,'points':points}); current=[]; points=0
        current.append(index); points+=amount
    if current: batches.append({'indices':current,'points':points})
    for i,b in enumerate(batches): b['index']=i; b['name']=f'batch_{i:05d}'
    return batches


def prepare(svg: Path, directory: Path, batch_size: int=40, allow_prepopulated: bool=False) -> dict:
    svg=svg.resolve(); directory=directory.resolve()
    if not svg.is_file(): raise FigureError('SVG file does not exist')
    job_path=directory/'job.json'
    if job_path.exists():
        prior=verify_job(directory)
        if digest(svg)!=prior['master_sha256']:
            raise FigureError('Input changed: create a new output directory, never reuse completed drawing groups for new geometry')
        return prior
    if not allow_prepopulated and directory.exists() and any(directory.iterdir()):
        raise FigureError('New jobs require an empty output directory; existing files will not be overwritten')
    cache=compile_svg(svg)
    directory.mkdir(parents=True,exist_ok=True)
    master=directory/'figure_master.svg'
    if svg!=master: atomic_bytes(master,svg.read_bytes())
    cache['batches']=make_batches(cache['atoms'],batch_size)
    cache['master_sha256']=digest(master)
    cache_path=directory/'geometry-cache.json'; write_json(cache_path,cache)
    job={'schema_version':'1.0','software_version':__version__,'job_id':uuid.uuid4().hex[:24],
         'created_utc':utc(),'master':'figure_master.svg','cache':'geometry-cache.json',
         'master_sha256':digest(master),'cache_sha256':digest(cache_path),
         'total_atoms':cache['total_atoms'],'total_points':cache['total_points'],
         'live_text_count':cache['live_text_count'],'batches':len(cache['batches']),
         'review_required':True,'illustrator_verified':False,
         'outputs':{'ai':'figure.ai','png':'figure.png'},
         'status':'prepared_not_drawn','preparation_environment':platform.system()}
    write_json(job_path,job)
    return job


def verify_job(directory: Path) -> dict:
    directory=directory.resolve(); job=read_json(directory/'job.json')
    if job.get('schema_version')!='1.0': raise FigureError('Unsupported job schema')
    if not isinstance(job.get('job_id'),str) or len(job['job_id'])!=24 or any(c not in '0123456789abcdef' for c in job['job_id']):
        raise FigureError('Invalid job id')
    # Fixed names only: reject path traversal and arbitrary cache references.
    if job.get('master')!='figure_master.svg' or job.get('cache')!='geometry-cache.json':
        raise FigureError('Job file paths must be the fixed local filenames')
    if (directory/'figure_master.svg').is_symlink() or (directory/'geometry-cache.json').is_symlink():
        raise FigureError('Job master and cache must not be symlinks')
    if digest(directory/'figure_master.svg')!=job['master_sha256']:
        raise FigureError('Master SVG hash mismatch')
    if digest(directory/'geometry-cache.json')!=job['cache_sha256']:
        raise FigureError('Geometry cache hash mismatch')
    cache=read_json(directory/'geometry-cache.json')
    if cache.get('master_sha256')!=job['master_sha256'] or cache.get('schema_version')!='1.0':
        raise FigureError('Cache provenance mismatch')
    if len(cache.get('atoms',[]))!=job['total_atoms']:
        raise FigureError('Cache object count mismatch')
    indices=[x for batch in cache['batches'] for x in batch['indices']]
    if indices!=list(range(len(cache['atoms']))):
        raise FigureError('Batch schedule does not cover each object exactly once in paint order')
    return job


def vector_job(image: Path, directory: Path, backend: str, text_mode: str,
               source: Path | None=None, manifest_path: Path | None=None, regions_path: Path | None=None, include_illustrator: bool=False, profile: str='auto') -> dict:
    directory=directory.resolve()
    if directory.exists() and any(directory.iterdir()):
        raise FigureError('Use an empty output directory; resume with figure_cli.py draw, not by retracing')
    image=image.resolve()
    with Image.open(image) as original:
        if original.width*original.height>8_000_000:
            raise FigureError('Input exceeds 8 megapixels; resize explicitly and update coordinates')
        if original.getexif().get(274,1)!=1:
            raise FigureError('Apply EXIF orientation explicitly before recording text coordinates')
        # Flatten transparency on white, record the normalized image used for trace / QA.
        rgba=original.convert('RGBA'); normalized=Image.new('RGBA',rgba.size,'white'); normalized.alpha_composite(rgba)
        normalized=normalized.convert('RGB')
    manifest=read_json(manifest_path) if manifest_path else None
    if text_mode=='manifest' and (source is None or manifest is None):
        raise FigureError('Editable-text mode requires --source-image and --text-manifest; image must already be text-cleaned')
    if text_mode!='manifest' and manifest is not None:
        raise FigureError('Manifest provided in the wrong text mode')
    if text_mode not in {'none','outlines','manifest'}:
        raise FigureError('Select an explicit text mode')
    cleanup=None
    if manifest is not None:
        cleanup=cleanup_audit(source,image,manifest)
    regions=read_json(regions_path).get('regions',[]) if regions_path else []
    directory.mkdir(parents=True,exist_ok=True)
    normalized.save(directory/'trace_input.png')
    atomic_bytes(directory/('input_original'+image.suffix), image.read_bytes())
    if source: atomic_bytes(directory/('text_source'+source.suffix),source.read_bytes())
    if manifest: write_json(directory/'text_manifest.json',manifest)
    ranked=rank_candidates(directory/'trace_input.png',directory/'candidates',backend,regions,include_illustrator,profile)
    selected=directory/'candidates'/ranked['selected']['svg']
    master=directory/'figure_master.svg'
    if manifest is not None: merge_text(selected,master,manifest,compile_result=False)
    else: atomic_bytes(master,selected.read_bytes())
    job=prepare(master,directory,allow_prepopulated=True)
    job.update({'input_sha256':digest(image),'backend':ranked['selected']['backend'],
                'text_mode':text_mode,'text_is_live':text_mode=='manifest',
                'source_sha256':digest(source) if source else None,'status':'prepared_review_required'})
    write_json(directory/'job.json',job)
    input_colors=normalized.getcolors(maxcolors=256)
    source_characteristics={'unique_colors_up_to_256':len(input_colors) if input_colors is not None else None,
        'more_than_256_colors':input_colors is None,
        'advisory':'Many colors can reflect antialiasing, gradients or photographs. Quantization may alter scientific color encodings; manual review remains mandatory.' if input_colors is None else None}
    report={'source_characteristics':source_characteristics,'created_utc':utc(),'selected':ranked['selected'],'candidates':ranked['candidates'],
            'failed_candidates':ranked['failed_candidates'],'cleanup':cleanup,
            'review_required':True,'text_mode':text_mode,'scientific_data_validated':False,
            'illustrator_tested':False,'limitations':['Raster similarity is not scientific correctness.',
                'Local preview is not an Illustrator rendering.', 'Native object editability still needs target-machine inspection.']}
    write_json(directory/'qa.json',report)
    rows=io.StringIO(newline=''); writer=csv.writer(rows)
    writer.writerow(['candidate','backend','objects','anchors','mae','foreground_mae','edge_f1','selection_score','heuristic_pass'])
    for c in ranked['candidates']:
        q=c['qa']; writer.writerow([c['svg'],c['backend']['engine'],c['path_objects'],c['anchors'],q['mae'],q['foreground_mae'],q['edge_f1_tolerance_1px'],c['selection_score'],q['heuristic_pass']])
    atomic_bytes(directory/'candidate_comparison.csv',('\ufeff'+rows.getvalue()).encode('utf-8'))
    return job
