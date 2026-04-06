"""zip writes for output pk3."""

import os
import time

ZIP_OUT_COMPRESSLEVEL = 3


def file_busy(e):
    if isinstance(e, PermissionError):
        return True
    if isinstance(e, OSError):
        if getattr(e, "winerror", None) == 32:
            return True
        if os.name == "nt" and e.errno == 13:
            return True
    return False


def zip_write_retry(zf, path, arcname):
    for attempt in range(12):
        try:
            zf.write(path, arcname)
            return
        except OSError as e:
            if file_busy(e) and attempt + 1 < 12:
                time.sleep(0.05 * (attempt + 1))
                continue
            raise
