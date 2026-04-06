"""shader text deps + ql-style patch."""

import os
import re

from .constants import BRANDING_COMMENT, BRANDING_TEXT
from .bsp import strip_ogg

SHADER_DEP_RX = tuple(
    re.compile(
        kw + r'\s+"?([^"\s\n\x00]+)"?',
        re.IGNORECASE,
    )
    for kw in (
        r"\bmap\b",
        r"\bclampmap\b",
        r"\bqer_editorimage\b",
        r"\bq3map_lightimage\b",
        r"\bsound\b",
    )
)
SHADER_ANIMMAP_RX = re.compile(r"animMap\s+[^\n]+", re.IGNORECASE)


def shader_deps(shader_content):
    deps = []
    for rx in SHADER_DEP_RX:
        deps.extend(rx.findall(shader_content))
    matches = SHADER_ANIMMAP_RX.findall(shader_content)
    for m in matches:
        parts = m.split()
        if len(parts) > 2:
            for p in parts[2:]:
                deps.append(p.strip('"'))
    return [d.lower().replace("\\", "/") for d in deps if d and not d.startswith("$")]


def fix_all_shaders(root: str) -> int:
    n = 0
    for dirname, _, files in os.walk(root):
        for f in files:
            if not f.lower().endswith(".shader"):
                continue
            ok, _, _ = process_shader(os.path.join(dirname, f))
            if ok:
                n += 1
    return n


def process_shader(filepath):
    try:
        with open(filepath, "rb") as f:
            content = f.read()
        text = content.decode("utf-8", errors="ignore")
        if BRANDING_TEXT[:20] not in text:
            text = BRANDING_COMMENT + text
        lower_text = text.lower()
        replacements = [(".dds", ".tga"), (".png", ".tga")]
        for old, new in replacements:
            idx = lower_text.find(old)
            while idx != -1:
                text = text[:idx] + new + text[idx + len(old) :]
                lower_text = lower_text[:idx] + new + lower_text[idx + len(old) :]
                idx = lower_text.find(old, idx + len(new))
        text = strip_ogg(text)
        with open(filepath, "wb") as f:
            f.write(text.encode("utf-8"))
        return True, None, text
    except Exception as e:
        return False, f"Shader error in {os.path.basename(filepath)}: {str(e)}", None
