#!/usr/bin/env python3
"""Local CLI. No model key, vectorization API, telemetry, or runtime downloads."""
from __future__ import annotations
import argparse
import importlib.metadata
import json
import os
import platform
import sys
import subprocess
from pathlib import Path
from figurelib.common import FigureError, read_json, write_json, require_new_output
from figurelib.svg import compile_svg
from figurelib.jobs import prepare, vector_job, verify_job
from figurelib.trace import available, normalize_svg
from figurelib.text import erase_flat, erase_rows, merge_text
from figurelib.preview import render_paths


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__); commands=p.add_subparsers(dest='command',required=True)
    commands.add_parser('doctor')
    q=commands.add_parser('illustrator-doctor'); q.add_argument('--app-path'); q.add_argument('--prog-id')
    q=commands.add_parser('draw'); q.add_argument('--job-dir',type=Path,required=True)
    q.add_argument('--approve-review',action='store_true'); q.add_argument('--dry-run',action='store_true')
    q.add_argument('--allow-overlap',action='store_true'); q.add_argument('--app-path'); q.add_argument('--prog-id')
    q.add_argument('--max-width-fraction',type=float,default=.72); q.add_argument('--max-height-fraction',type=float,default=.78)
    q.add_argument('--checkpoint-seconds',type=int,default=30)
    q=commands.add_parser('native-test'); q.add_argument('--out-dir',type=Path,required=True)
    q.add_argument('--create-document',action='store_true'); q.add_argument('--confirm-empty-document',action='store_true')
    q.add_argument('--app-path'); q.add_argument('--prog-id')
    q=commands.add_parser('trace-native'); q.add_argument('--image',type=Path,required=True); q.add_argument('--output',type=Path,required=True)
    q.add_argument('--colors',type=int,default=32); q.add_argument('--allow-temporary-document',action='store_true')
    q.add_argument('--app-path'); q.add_argument('--prog-id')
    q=commands.add_parser('validate'); q.add_argument('--svg',type=Path,required=True)
    q=commands.add_parser('prepare'); q.add_argument('--svg',type=Path,required=True); q.add_argument('--out-dir',type=Path,required=True); q.add_argument('--batch-size',type=int,default=40)
    q=commands.add_parser('verify-job'); q.add_argument('--job-dir',type=Path,required=True)
    q=commands.add_parser('vectorize'); q.add_argument('--image',type=Path,required=True); q.add_argument('--out-dir',type=Path,required=True)
    q.add_argument('--backend',choices=['auto','vtracer-cli','vtracer-python','contours'],default='auto')
    q.add_argument('--profile',choices=['auto','balanced','fine','faithful'],default='auto')
    q.add_argument('--text-mode',choices=['none','outlines','manifest'],required=True)
    q.add_argument('--source-image',type=Path); q.add_argument('--text-manifest',type=Path); q.add_argument('--regions',type=Path)
    q.add_argument('--allow-illustrator-temp-document',action='store_true',help='Explicitly authorize native Image Trace candidates in a temporary document on Windows/macOS')
    q=commands.add_parser('erase-text'); q.add_argument('--source-image',type=Path,required=True); q.add_argument('--text-manifest',type=Path,required=True); q.add_argument('--output',type=Path,required=True); q.add_argument('--confirm-flat-background-boxes',action='store_true')
    q.add_argument('--method',choices=['flat','row-sample'],default='flat'); q.add_argument('--confirm-background-boxes',action='store_true')
    q=commands.add_parser('merge-text'); q.add_argument('--svg',type=Path,required=True); q.add_argument('--text-manifest',type=Path,required=True); q.add_argument('--output',type=Path,required=True)
    q=commands.add_parser('preview'); q.add_argument('--svg',type=Path,required=True); q.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.command=='doctor':
            versions={}
            for name in ['Pillow','numpy','opencv-python-headless','fonttools','defusedxml','vtracer']:
                try: versions[name]=importlib.metadata.version(name)
                except importlib.metadata.PackageNotFoundError: versions[name]='not installed'
            result={'python':sys.version,'platform':platform.platform(),'backends':available(),'dependencies':versions,
                    'illustrator_automation_supported_on_this_os':platform.system() in ('Windows','Darwin'),'illustrator_verified':False,
                    'network_in_core':False,'note':'Run illustrator-doctor to inspect the already-open native application.'}
        elif args.command=='illustrator-doctor':
            from figurelib.illustrator import Bridge, probe
            with Bridge(args.app_path,args.prog_id) as host: result=probe(host)
        elif args.command=='draw':
            from figurelib.illustrator import draw
            result=draw(args.job_dir,args.approve_review,args.dry_run,args.allow_overlap,
                args.max_width_fraction,args.max_height_fraction,args.checkpoint_seconds,args.app_path,args.prog_id)
        elif args.command=='native-test':
            from figurelib.illustrator import native_test
            result=native_test(args.out_dir,args.create_document,args.confirm_empty_document,args.app_path,args.prog_id)
        elif args.command=='trace-native':
            from figurelib.illustrator import native_trace
            result=native_trace(args.image,args.output,args.colors,args.allow_temporary_document,args.app_path,args.prog_id)
        elif args.command=='validate':
            c=compile_svg(args.svg); result={k:v for k,v in c.items() if k!='atoms'}
        elif args.command=='prepare': result=prepare(args.svg,args.out_dir,args.batch_size)
        elif args.command=='verify-job': result=verify_job(args.job_dir)
        elif args.command=='vectorize': result=vector_job(args.image,args.out_dir,args.backend,args.text_mode,args.source_image,args.text_manifest,args.regions,args.allow_illustrator_temp_document,args.profile)
        elif args.command=='erase-text':
            method=erase_rows if args.method=='row-sample' else erase_flat
            method(args.source_image,args.output,read_json(args.text_manifest),args.confirm_background_boxes or args.confirm_flat_background_boxes); result={'output':str(args.output.resolve()),'method':args.method}
        elif args.command=='merge-text':
            c=merge_text(args.svg,args.output,read_json(args.text_manifest)); result={'output':str(args.output.resolve()),'live_text_count':c['live_text_count']}
        elif args.command=='preview':
            require_new_output(args.output,args.svg)
            im=render_paths(compile_svg(args.svg)); args.output.parent.mkdir(parents=True,exist_ok=True); im.save(args.output); result={'output':str(args.output.resolve()),'publication_render':False}
        print(json.dumps({'ok':True,'result':result},ensure_ascii=False,indent=2,allow_nan=False))
        return 0
    except (FigureError,OSError,ValueError,subprocess.SubprocessError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
