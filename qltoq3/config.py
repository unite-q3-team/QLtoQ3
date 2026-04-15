from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .l10n import default_lang_from_env


def get_gui_state_file() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return Path(base) / "qltoq3" / "gui_state.json"
    return Path.home() / ".config" / "qltoq3" / "gui_state.json"


def default_gui_state(bd: str, root: str) -> dict[str, Any]:
    lg = default_lang_from_env()
    if lg not in ("en", "ru"):
        lg = "en"
    return {
        "version": 1,
        "lang": lg,
        "input_mode": "local",
        "output": "q3",
        "paths": [],
        "workshop_list": [],
        "collection_list": [],
        "yes_always": False,
        "force": False,
        "no_aas": False,
        "optimize": False,
        "dry_run": False,
        "hide_converted": False,
        "skip_mapless": False,
        "verbose": False,
        "show_skipped": False,
        "time_stages": False,
        "check_updates_on_start": True,
        "auto_download_update": False,
        "latest_known_version": "",
        "no_aas_optimize": False,
        "aas_geometry_fast": False,
        "aas_bspc_breadthfirst": False,
        "aas_timeout": 90,
        "coworkers": 3,
        "pool_max": 96,
        "bspc_concurrent": 1,
        "bsp_patch_method": 1,
        "aas_threads": "",
        "bspc": os.path.join(bd, "bspc.exe"),
        "levelshot": os.path.join(bd, "levelshot.png"),
        "steamcmd": r"c:\steamcmd\steamcmd.exe",
        "ffmpeg": "ffmpeg",
        "ql_pak": os.path.join(root, "ql_baseq3", "pak00.pk3"),
        "log": "",
    }


def merge_gui_state(raw: dict[str, Any], bd: str, root: str) -> dict[str, Any]:
    base = default_gui_state(bd, root)
    base.update(raw)
    if base.get("lang") not in ("en", "ru"):
        base["lang"] = default_gui_state(bd, root)["lang"]
    if base.get("input_mode") not in ("local", "steam"):
        base["input_mode"] = "local"
    return base


def save_gui_state(state: dict[str, Any]) -> None:
    path = get_gui_state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_gui_state() -> dict[str, Any] | None:
    path = get_gui_state_file()
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict):
        return raw
    return None
