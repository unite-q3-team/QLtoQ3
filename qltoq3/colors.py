"""ansi colors; off with NO_COLOR or --no-color."""

import os
import re


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ORANGE = "\033[38;5;208m"
    DARK_GRAY = "\033[38;5;240m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def use_color_from_env() -> bool:
    if os.environ.get("NO_COLOR", "").strip():
        return False
    return True


def disable_colors() -> None:
    for name in (
        "HEADER",
        "BLUE",
        "CYAN",
        "GREEN",
        "YELLOW",
        "RED",
        "ORANGE",
        "DARK_GRAY",
        "ENDC",
        "BOLD",
    ):
        setattr(Colors, name, "")


def apply_gradient(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text
    if not Colors.CYAN and not Colors.ENDC:
        return text
    colors = [214, 208, 202, 196, 160, 196, 202, 208, 214]
    result = []
    for i, line in enumerate(lines):
        color_idx = int((i / len(lines)) * (len(colors) - 1))
        color_code = colors[color_idx]
        result.append(f"\033[38;5;{color_code}m{line}\033[0m")
    return "\n".join(result)


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)
