"""paths + static blobs for ql->q3."""

import os

BUNDLED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "bundled"))

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def bundled_dir() -> str:
    return BUNDLED_DIR


def repo_root() -> str:
    return REPO_ROOT


BANNER_RULE_WIDTH = 51


def banner_rule_line(title: str = "", fill: str = "=") -> str:
    width = BANNER_RULE_WIDTH
    t = title.strip()
    if not t:
        return fill * width
    inner = f" {t} "
    if len(inner) > width:
        return (t + fill * width)[:width]
    pad = width - len(inner)
    left = pad // 2
    right = pad - left
    return fill * left + inner + fill * right


EXPECTED_PAK00_SHA256 = (
    "7d5fd8d4786f9e140804b7279ce2589c8a7babdcf2886763a63a992ad9ef634b"
)


def pak00_ref():
    fp = os.path.join(BUNDLED_DIR, "expected_pak00.sha256")
    if os.path.isfile(fp):
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if len(line) >= 64:
                    cand = line[:64]
                    if all(c in "0123456789abcdefABCDEF" for c in cand):
                        return cand.lower()
    if EXPECTED_PAK00_SHA256 and str(EXPECTED_PAK00_SHA256).strip():
        v = "".join(str(EXPECTED_PAK00_SHA256).strip().split())
        if len(v) == 64 and all(c in "0123456789abcdefABCDEF" for c in v):
            return v.lower()
    return None


BRANDING_TEXT = "\n=============================\nthis pk3 was converted using QLtoQ3 tool by q3unite.su\nfeel free to visit, join the community and play on our servers\n============================="
BRANDING_COMMENT = "// " + BRANDING_TEXT.replace("\n", "\n// ") + "\n\n"

ENTITY_REPLACEMENTS = {
    "item_armor_heavy": "item_armor_body",
    "item_armor_medium": "item_armor_combat",
    "weapon_hmg": "weapon_machinegun",
    "weapon_chaingun": "weapon_minigun",
    "weapon_nailgun": "weapon_plasmagun",
    "weapon_prox_launcher": "weapon_grenadelauncher",
}

SPLASH = r"""═══════════════════════════════════════════════════
  ▄▄▄▄      ▄▄▄                    ▄▄▄▄     ▄▄▄▄▄  
▄█▀▀███▄▄  ▀██▀       █▄         ▄█▀▀███▄▄ ██▀▀▀██ 
██    ██    ██       ▄██▄        ██    ██  ▀   ▄█▀ 
██    ██    ██        ██ ▄███▄   ██    ██    ▀▀▀█▄ 
██  ▄ ██    ██        ██ ██ ██   ██  ▄ ██  ▄    ██ 
 ▀█████▄   ████████  ▄██▄▀███▀    ▀█████▄  ▀█████▀ 
      ▀█                               ▀█          
                                     pk3 converter
═══════════════════════════════════════════════════

               ⣇⡀ ⡀⢀ ⠄ ⡇ ⣰⡀   ⣇⡀ ⡀⢀ 
               ⠧⠜ ⠣⠼ ⠇ ⠣ ⠘⠤   ⠧⠜ ⣑⡺ 
         ⢀⣀ ⢉⡹ ⡀⢀ ⣀⡀ ⠄ ⣰⡀ ⢀⡀   ⢀⣀ ⡀⢀
         ⠣⢼ ⠤⠜ ⠣⠼ ⠇⠸ ⠇ ⠘⠤ ⠣⠭ ⠶ ⠭⠕ ⠣⠼

═══════════════════════════════════════════════════
"""
