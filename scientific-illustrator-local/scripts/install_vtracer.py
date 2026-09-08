#!/usr/bin/env python3
"""Explicit opt-in download of an official pinned VTracer CLI. Never called per-image."""
from __future__ import annotations
import argparse
import hashlib
import io
import os
import platform
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile

VERSION='1.0.0-alpha.4'
# SHA256 digests returned by the official GitHub release API on 2026-09-08.
ASSETS={
 ('Windows','AMD64'):('vtracer-x86_64-pc-windows-msvc.zip','8eadb5529864265f003f791ad9cb128e1b9b8b8af8c21016f38b04706bcf3531'),
 ('Windows','x86_64'):('vtracer-x86_64-pc-windows-msvc.zip','8eadb5529864265f003f791ad9cb128e1b9b8b8af8c21016f38b04706bcf3531'),
 ('Linux','x86_64'):('vtracer-x86_64-unknown-linux-musl.tar.gz','2058f611b48ed49497f78883bde47435531e9e17e3a79428432d1528bdb12e2a'),
 ('Darwin','arm64'):('vtracer-aarch64-apple-darwin.tar.gz','71132b7781dc38b6a98917078b04e7353a3885916c5a224bc5e1154627b3d5f2'),
 ('Darwin','x86_64'):('vtracer-x86_64-apple-darwin.tar.gz','22f06d100d2b0cbd7b5efc222b68bebf817865b34a0caa949fd2f4d608a76182'),
}


def unpack_executable(data: bytes, asset: str, expected_hash: str) -> bytes:
    if hashlib.sha256(data).hexdigest()!=expected_hash:
        raise ValueError('Official release checksum mismatch. Do not execute this download.')
    expected='vtracer.exe' if asset.endswith('.zip') else 'vtracer'
    if asset.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names=[i for i in z.infolist() if Path(i.filename).name==expected and not i.is_dir()]
            if len(names)!=1 or names[0].file_size>20_000_000:
                raise ValueError('Unexpected archive layout')
            # Read selected bytes only. Never extract arbitrary archive paths or symlinks.
            return z.read(names[0])
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
        names=[m for m in t.getmembers() if Path(m.name).name==expected and m.isfile()]
        if len(names)!=1 or names[0].size>20_000_000:
            raise ValueError('Unexpected archive layout')
        f=t.extractfile(names[0])
        if f is None: raise ValueError('Cannot read executable')
        return f.read()


def install(destination: Path) -> Path:
    key=(platform.system(),platform.machine())
    if key not in ASSETS: raise RuntimeError(f'No pinned executable for {key}. Use contours or install VTracer yourself.')
    asset,sha=ASSETS[key]
    destination=destination.resolve();destination.mkdir(parents=True,exist_ok=True)
    target=destination/('vtracer.exe' if key[0]=='Windows' else 'vtracer')
    if target.exists(): raise FileExistsError(f'{target} already exists; refusing silent replacement')
    url=f'https://github.com/visioncortex/vtracer/releases/download/{VERSION}/{asset}'
    request=urllib.request.Request(url,headers={'User-Agent':'Scientific-Illustrator-Local-Installer/0.1'})
    with urllib.request.urlopen(request,timeout=60) as response:
        data=response.read(20_000_001)
    if len(data)>20_000_000: raise ValueError('Download exceeds maximum archive size')
    payload=unpack_executable(data,asset,sha)
    fd,tmp=tempfile.mkstemp(dir=destination,prefix='.vtracer-')
    try:
        with os.fdopen(fd,'wb') as f:f.write(payload)
        os.chmod(tmp,0o755);os.replace(tmp,target)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    (destination/'vtracer-provenance.txt').write_text(f'version={VERSION}\nsource={url}\narchive_sha256={sha}\nexecutable_sha256={hashlib.sha256(payload).hexdigest()}\n',encoding='utf-8')
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
    try:print(install(a.destination))
    except Exception as e:raise SystemExit(f'VTracer installation failed: {e}')
