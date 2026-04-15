from __future__ import annotations

from .base import BaseTab


class LogsTab(BaseTab):
    def build(self) -> None:
        self.app._setup_log_tab()

    def get_state(self) -> dict[str, str]:
        return {"log": self.app._log_path.get().strip()}

    def on_scroll(self, *args: object) -> None:
        self.app._on_log_scroll(*args)

    def check_at_bottom(self) -> bool:
        return self.app._check_log_at_bottom()

    def clear(self) -> None:
        self.app._clear_log()

    def copy(self) -> None:
        self.app._copy_log()

    def save(self) -> None:
        self.app._save_log_to_file()

    def append_chunk(self, chunk: str) -> None:
        self.app._append_log_chunk(chunk)

