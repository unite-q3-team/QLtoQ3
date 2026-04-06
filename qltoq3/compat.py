"""quick check: archive already q3-ish."""

import os
import struct
import zipfile


# monkeycode to decide if pk3 is q3 or ql compatible
# and needs to be converted
def q3_compat(in_pk3):
    try:
        with zipfile.ZipFile(in_pk3, "r") as zf:
            has_bsp = False
            for n in zf.namelist():
                if os.path.splitext(n)[1].lower() in [".dds", ".png", ".ogg"]:
                    return False
                if n.lower().endswith(".bsp"):
                    has_bsp = True
                    with zf.open(n) as f:
                        h = f.read(8)
                        if (
                            len(h) >= 8
                            and h[0:4] == b"IBSP"
                            and struct.unpack("<I", h[4:8])[0] > 46
                        ):
                            return False
            if not has_bsp:
                return False
    except Exception:
        return False
    return True
