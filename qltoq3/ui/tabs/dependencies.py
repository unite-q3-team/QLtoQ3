from __future__ import annotations

from typing import Any

from .base import BaseTab


class DependenciesTab(BaseTab):
    def build(self) -> None:
        self.app._setup_tools(self.app._bd, self.app._repo_root)

    def get_state(self) -> dict[str, Any]:
        return {
            "bspc": self.app._path["bspc"].get().strip(),
            "levelshot": self.app._path["levelshot"].get().strip(),
            "steamcmd": self.app._path["steamcmd"].get().strip(),
            "ffmpeg": self.app._path["ffmpeg"].get().strip(),
            "ql_pak": self.app._path["ql_pak"].get().strip(),
            "log": self.app._log_path.get().strip(),
        }

    def browse_tool(self, key: str, pick_dir: bool = False) -> None:
        self.app._browse_tool(key, pick_dir=pick_dir)

    def refresh_all_statuses(self) -> None:
        self.app._refresh_all_tool_path_status()

    def check_status(self, key: str) -> tuple[bool, str]:
        return self.app._check_tool_path_status(key)

    def open_download_link(self, key: str) -> None:
        self.app._tool_download_link(key)

