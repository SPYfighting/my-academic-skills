from __future__ import annotations
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

class FigureError(ValueError):
    """Actionable validation error; do not silently change a user's artwork."""

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def atomic_bytes(path: Path, content: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def write_json(path: Path, data: Any) -> None:
    atomic_bytes(path, (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))

def read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_constant=lambda s: (_ for _ in ()).throw(FigureError('Non-finite JSON value: ' + s)))
    except (ValueError, OSError) as exc:
        raise FigureError(f'Cannot read JSON {path}: {exc}') from exc

def finite(value: Any, name: str = 'number') -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise FigureError(f'{name} must be numeric') from exc
    if not math.isfinite(result) or abs(result) > 1e9:
        raise FigureError(f'{name} must be finite and within +/- 1e9')
    return result


def require_new_output(output: Path, *inputs: Path) -> None:
    """Transform commands must never overwrite input or any pre-existing output."""
    output = Path(output)
    if any(output.resolve() == Path(source).resolve() for source in inputs):
        raise FigureError('Output must not replace an input file; choose a new filename')
    if output.exists() or output.is_symlink():
        raise FigureError('Output already exists; choose a new filename instead of overwriting it')
