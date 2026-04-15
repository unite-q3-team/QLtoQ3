from __future__ import annotations

from tkinter import END
from typing import Any

from .base import BaseTab


class SourcesTab(BaseTab):
    def build(self) -> None:
        self.app._setup_home()

    def get_state(self) -> dict[str, Any]:
        return {
            "output": self.app._out.get().strip(),
            "paths": list(self.app._listbox.get(0, END)),
            "workshop_list": list(self.app._ws_listbox.get(0, END)),
            "collection_list": list(self.app._col_listbox.get(0, END)),
            "_has_inputs": bool(
                list(self.app._listbox.get(0, END))
                or list(self.app._ws_listbox.get(0, END))
                or list(self.app._col_listbox.get(0, END))
            ),
        }

    def add_files(self) -> None:
        self.app._add_files()

    def add_dir(self) -> None:
        self.app._add_dir()

    def remove_selected(self) -> None:
        self.app._remove_sel()

    def clear(self) -> None:
        self.app._clear_list()

    def browse_output(self) -> None:
        self.app._browse_out()

    def open_output(self) -> None:
        self.app._open_out()

    def on_mode_change(self, value: str) -> None:
        self.app._on_in_mode(value)

    def refresh_placeholder(self) -> None:
        self.app._refresh_local_placeholder()

