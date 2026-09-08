#!/usr/bin/env python3
"""Create dependencies beside this skill only. Never register a global agent skill."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parents[1]


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--with-vtracer',action='store_true',help='Explicitly download the pinned official executable after verifying its SHA256')
    p.add_argument('--offline-wheelhouse',type=Path,help='Install Python wheels from this local directory without using PyPI')
    p.add_argument('--check',action='store_true',help='Read-only: inspect the skill environment; do not install anything')
    args=p.parse_args(argv)
    if not (3,11)<=sys.version_info[:2]<(3,14):
        p.error('Run this installer with CPython 3.11, 3.12 or 3.13')
    env=ROOT/'.venv';python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if args.check:
        if not python.is_file(): p.error('Skill-local .venv is absent; run setup_environment.py once')
    else:
        if env.exists() and not (env/'pyvenv.cfg').is_file():
            p.error('Existing .venv is not a virtual environment; refusing to replace it')
        if not env.exists(): venv.EnvBuilder(with_pip=True).create(env)
        command=[str(python),'-m','pip','install','--only-binary=:all:','-r',str(ROOT/'requirements.lock')]
        if args.offline_wheelhouse:
            command+=['--no-index','--find-links',str(args.offline_wheelhouse.resolve())]
        subprocess.run(command,check=True)
        if args.with_vtracer:
            from install_vtracer import install
            install(ROOT/'bin')
    subprocess.run([str(python),'-X','utf8',str(ROOT/'scripts/figure_cli.py'),'doctor'],check=True)
    return 0


if __name__=='__main__':
    try: raise SystemExit(main())
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        print('Environment setup failed: '+str(exc),file=sys.stderr);raise SystemExit(2)
