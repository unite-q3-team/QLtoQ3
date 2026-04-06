"""ibsp patch + entity string."""

import os
import re
import struct

from .constants import ENTITY_REPLACEMENTS

# q3 IBSP lump indices and element sizes for stats
_LUMP_NODES = 3
_LUMP_LEAFS = 4
_LUMP_BRUSHES = 8
_LUMP_BRUSHSIDES = 9
_LUMP_DRAWVERTS = 10
_LUMP_SURFACES = 13

_SZ_NODE = 12
_SZ_LEAF = 48
_SZ_BRUSH = 12
_SZ_BRUSHSIDE = 8
_SZ_DRAWVERT = 44
_SZ_SURFACE = 104


def _short_num(n: int) -> str:
    if n >= 1_000_000:
        x = n / 1_000_000
        s = f"{x:.1f}".rstrip("0").rstrip(".")
        return f"{s}M"
    if n >= 1000:
        x = n / 1000
        s = f"{x:.1f}".rstrip("0").rstrip(".")
        return f"{s}k"
    return str(n)


def bsp_geometry_hint(filepath: str) -> str | None:
    """
    compact IBSP complexity string for bspc progress (brushes / sides / verts / etc)
    uses lump byte sizes from the BSP on disk (same file bspc reads)
    """
    try:
        sz = os.path.getsize(filepath)
        with open(filepath, "rb") as f:
            hdr = f.read(8 + 64 * 8)
    except OSError:
        return None
    if len(hdr) < 8 + 64 * 8 or hdr[0:4] != b"IBSP":
        return None
    ver = struct.unpack("<I", hdr[4:8])[0]
    if ver not in (46, 47):
        return None

    def lump_len(i: int) -> int:
        o, ln = struct.unpack("<II", hdr[8 + i * 8 : 8 + i * 8 + 8])
        if o < 0 or ln < 0 or o + ln > sz:
            return 0
        return ln

    n_nodes = lump_len(_LUMP_NODES) // _SZ_NODE
    n_leafs = lump_len(_LUMP_LEAFS) // _SZ_LEAF
    n_brushes = lump_len(_LUMP_BRUSHES) // _SZ_BRUSH
    n_bsides = lump_len(_LUMP_BRUSHSIDES) // _SZ_BRUSHSIDE
    n_verts = lump_len(_LUMP_DRAWVERTS) // _SZ_DRAWVERT
    n_surf = lump_len(_LUMP_SURFACES) // _SZ_SURFACE

    if max(n_brushes, n_verts, n_surf, n_bsides) <= 0:
        return None

    ordered = (
        ("br", n_brushes),
        ("bs", n_bsides),
        ("lf", n_leafs),
        ("nd", n_nodes),
        ("v", n_verts),
        ("sf", n_surf),
    )
    parts = [f"{a}:{_short_num(b)}" for a, b in ordered if b > 0]
    return " ".join(parts[:5]) if parts else None


def strip_ogg(text):
    return re.sub(r'\.ogg(?=["\s\n\r;,]|$)', "", text, flags=re.IGNORECASE)


def patch_entities(ent_string):
    longname = "Unknown Map"
    match = re.search(r'"message"\s+"([^"]+)"', ent_string)
    if match:
        longname = match.group(1)
    deps = []
    for key in ["noise", "music", "model", "model2"]:
        found = re.findall(rf'"{key}"\s+"([^"]+)"', ent_string, re.IGNORECASE)
        deps.extend([f.lower().replace("\\", "/") for f in found if f])
    for old, new in ENTITY_REPLACEMENTS.items():
        ent_string = ent_string.replace(f'"{old}"', f'"{new}"')
    ent_string = strip_ogg(ent_string)
    return ent_string, longname, deps


def process_bsp(filepath, method=1):
    issues = []
    try:
        with open(filepath, "rb") as f:
            data = bytearray(f.read())
    except Exception as e:
        return (
            [],
            "Unknown",
            [],
            [f"Failed to read BSP {os.path.basename(filepath)}: {str(e)}"],
        )

    if data[0:4] != b"IBSP":
        return [], "Unknown", [], [f"Not a valid IBSP: {os.path.basename(filepath)}"]

    lump1_offset, lump1_length = struct.unpack("<II", data[16:24])
    num_textures = lump1_length // 72
    used_textures = []
    for i in range(num_textures):
        start = lump1_offset + i * 72
        name_str = (
            data[start : start + 64].split(b"\x00")[0].decode("ascii", errors="ignore")
        )
        used_textures.append(name_str.lower().replace("\\", "/"))
        version = struct.unpack("<I", data[4:8])[0]
        if version == 47:
            new_name_str = name_str
            for ext in [".dds", ".png"]:
                if new_name_str.lower().endswith(ext):
                    new_name_str = new_name_str[:-4] + ".tga"
            if new_name_str != name_str:
                new_bytes = new_name_str.encode("ascii")[:63] + b"\x00" * (
                    64 - len(new_name_str.encode("ascii")[:63])
                )
                data[start : start + 64] = new_bytes

    if struct.unpack("<I", data[4:8])[0] == 47:
        data[4:8] = struct.pack("<I", 46)

    ent_offset, ent_len = struct.unpack("<II", data[8:16])
    ent_data = data[ent_offset : ent_offset + ent_len].decode("ascii", errors="ignore")
    new_ents, longname, ent_deps = patch_entities(ent_data)
    new_ent_bytes = new_ents.encode("ascii")

    if len(new_ent_bytes) <= ent_len:
        data[ent_offset : ent_offset + ent_len] = new_ent_bytes.ljust(ent_len, b"\x00")
    else:
        if method == 2:
            new_offset = len(data)
            new_length = len(new_ent_bytes)
            data.extend(new_ent_bytes)
            data[8:12] = struct.pack("<I", new_offset)
            data[12:16] = struct.pack("<I", new_length)
        else:
            issues.append(
                f"Entity string for {os.path.basename(filepath)} is too long ({len(new_ent_bytes)} > {ent_len}). Use --bsp-patch-method 2 to fix."
            )

    try:
        with open(filepath, "wb") as f:
            f.write(data)
    except Exception as e:
        issues.append(f"Failed to write BSP {os.path.basename(filepath)}: {str(e)}")

    return used_textures, longname, ent_deps, issues


def patch_all_bsps(root: str, method: int = 1) -> tuple[list[str], list[str]]:
    names: list[str] = []
    deps: list[str] = []
    for dirname, _, files in os.walk(root):
        for f in files:
            if not f.lower().endswith(".bsp"):
                continue
            fp = os.path.join(dirname, f)
            texs, _, ent_deps, _ = process_bsp(fp, method=method)
            deps.extend(texs)
            deps.extend(ent_deps)
            names.append(f)
    return names, deps
