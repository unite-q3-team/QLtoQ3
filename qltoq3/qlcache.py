"""cache lower-case paths into ql pk3 zip member names."""

import json
import os
import threading
import zipfile
from collections import OrderedDict
from typing import Any

from .constants import repo_root


class AssetIndex:
    __slots__ = ("data",)

    def __init__(self, data: dict[str, Any]):
        self.data = data

    @classmethod
    def load(cls, path: str) -> "AssetIndex":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))


QL_PK3_NAMEMAP_LOCK = threading.Lock()
QL_PK3_NAMEMAP_MAX = 96
QL_PK3_NAMEMAP: "OrderedDict[str, tuple[float, dict[str, str]]]" = OrderedDict()


def ql_pk3_lower_namemap(pk3_path: str):
    try:
        st = os.stat(pk3_path)
    except OSError:
        return None
    mtime = st.st_mtime
    ap = os.path.normcase(os.path.abspath(pk3_path))
    with QL_PK3_NAMEMAP_LOCK:
        ent = QL_PK3_NAMEMAP.get(ap)
        if ent is not None and ent[0] == mtime:
            QL_PK3_NAMEMAP.move_to_end(ap)
            return ent[1]
    try:
        with zipfile.ZipFile(pk3_path, "r") as zf:
            m = {n.lower().replace("\\", "/"): n for n in zf.namelist()}
    except (OSError, zipfile.BadZipFile, RuntimeError):
        return None
    with QL_PK3_NAMEMAP_LOCK:
        ent = QL_PK3_NAMEMAP.get(ap)
        if ent is not None and ent[0] == mtime:
            QL_PK3_NAMEMAP.move_to_end(ap)
            return ent[1]
        QL_PK3_NAMEMAP[ap] = (mtime, m)
        QL_PK3_NAMEMAP.move_to_end(ap)
        while len(QL_PK3_NAMEMAP) > QL_PK3_NAMEMAP_MAX:
            QL_PK3_NAMEMAP.popitem(last=False)
    return m


def ql_read(filename, ql_file_map, issues=None, ql_pak00_path=None):
    key = filename.lower().replace("\\", "/")
    pk3_name = ql_file_map.get(key)
    if pk3_name:
        root = repo_root()
        candidates = []
        if (
            pk3_name.lower() == "pak00.pk3"
            and ql_pak00_path
            and os.path.isfile(ql_pak00_path)
        ):
            candidates.append(os.path.abspath(ql_pak00_path))
        candidates.append(os.path.join(root, pk3_name))
        candidates.append(os.path.join(root, "ql_baseq3", pk3_name))
        seen = set()
        ordered = []
        for p in candidates:
            ap = os.path.normcase(os.path.abspath(p))
            if ap in seen:
                continue
            seen.add(ap)
            ordered.append(p)
        for p in ordered:
            if not os.path.exists(p):
                continue
            try:
                nm = ql_pk3_lower_namemap(p)
                if nm is None:
                    continue
                real = nm.get(key)
                if real is None:
                    continue
                with zipfile.ZipFile(p, "r") as zf:
                    return zf.read(real)
            except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as e:
                if issues is not None:
                    issues.append(f"QL pk3 read {pk3_name}: {e}")
    return None
