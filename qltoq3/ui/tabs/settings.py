from __future__ import annotations

from typing import Any

from .base import BaseTab


_CHECKBOX_KEYS = (
    "yes_always",
    "force",
    "no_aas",
    "optimize",
    "dry_run",
    "hide_converted",
    "skip_mapless",
    "verbose",
    "show_skipped",
    "time_stages",
    "no_aas_optimize",
    "aas_geometry_fast",
    "aas_bspc_breadthfirst",
)


class SettingsTab(BaseTab):
    def build(self) -> None:
        self.app._setup_settings()

    def get_state(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key in _CHECKBOX_KEYS:
            out[key] = self.app._chk[key][0].get() == 1
        out.update(
            {
                "aas_timeout": int(self.app._num["aas_timeout"].get() or "90"),
                "coworkers": int(self.app._num["coworkers"].get() or "3"),
                "pool_max": int(self.app._num["pool_max"].get() or "96"),
                "bspc_concurrent": int(self.app._num["bspc_concurrent"].get() or "1"),
                "bsp_patch_method": int(self.app._bsp_patch.get() or "1"),
                "aas_threads": self.app._aas_threads.get().strip(),
            }
        )
        return out

    def validate_num(self, entry: Any, default: int, min_v: int = 0, max_v: int | None = None) -> None:
        self.app._validate_num(entry, default, min_v=min_v, max_v=max_v)

    def reset_defaults(self) -> None:
        self.app._reset_gui_defaults()

