from __future__ import annotations

from typing import Any


class BaseTab:
    def __init__(self, app: Any) -> None:
        self.app = app

    def build(self) -> None:
        raise NotImplementedError

