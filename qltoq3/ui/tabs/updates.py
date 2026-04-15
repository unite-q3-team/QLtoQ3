from __future__ import annotations

from typing import Any

from .base import BaseTab


class UpdatesTab(BaseTab):
    def build(self) -> None:
        self.app._setup_updates()

    def get_state(self) -> dict[str, Any]:
        return {
            "check_updates_on_start": self.app._chk["check_updates_on_start"][0].get() == 1,
            "auto_download_update": self.app._chk["auto_download_update"][0].get() == 1,
            "latest_known_version": self.app._latest_known_version,
        }

    def start_check(self) -> None:
        self.app._start_update_check()

    def run_check_worker(self) -> None:
        self.app._update_check_worker()

    def on_check_done(self, latest: str, err: str | None) -> None:
        self.app._on_update_check_done(latest, err)

    def start_download(self) -> None:
        self.app._start_update_download()

    def run_download_worker(self, version: str) -> None:
        self.app._update_download_worker(version)

    def on_download_done(self, ok: bool, message: str, version: str) -> None:
        self.app._on_update_download_done(ok, message, version)

    def refresh_latest_label(self) -> None:
        self.app._refresh_latest_version_label()

    def refresh_install_button(self) -> None:
        self.app._refresh_update_install_button()

