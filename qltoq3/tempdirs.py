from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

TMP_PREFIX = "qltoq3_"


def find_stale_temp_dirs() -> list[Path]:
    base = Path(tempfile.gettempdir())
    out: list[Path] = []
    try:
        for p in base.iterdir():
            if p.is_dir() and p.name.startswith(TMP_PREFIX):
                out.append(p)
    except OSError:
        return []
    return sorted(out, key=lambda x: x.name)


def remove_temp_dirs(paths: list[Path]) -> tuple[int, int]:
    removed = 0
    failed = 0
    for p in paths:
        try:
            shutil.rmtree(p, ignore_errors=False)
            removed += 1
        except OSError:
            failed += 1
    return removed, failed
