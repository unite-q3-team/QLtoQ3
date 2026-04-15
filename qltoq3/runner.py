from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Callable

from .colors import strip_ansi

_PROGRESS_RE = re.compile(r"^QLTOQ3_PROGRESS\s+(\d+)/(\d+)(?:\s+(.*))?\s*$")
_PHASE_RE = re.compile(r"^QLTOQ3_PHASE\s+(\S+)\s+(\d+)\s*$")
_ACTION_RE = re.compile(r"^QLTOQ3_ACTION\s+(.*)\s*$")


def build_argv(state: dict[str, Any]) -> list[str]:
    argv: list[str] = [
        "--no-color",
        "--lang",
        state["lang"],
        "--output",
        state["output"],
    ]
    argv.extend(["--aas-timeout", str(int(state["aas_timeout"]))])
    argv.extend(["--coworkers", str(int(state["coworkers"]))])
    argv.extend(["--pool-max", str(int(state["pool_max"]))])
    argv.extend(["--bspc-concurrent", str(int(state["bspc_concurrent"]))])
    argv.extend(["--bsp-patch-method", str(int(state["bsp_patch_method"]))])
    at = (state.get("aas_threads") or "").strip()
    if at:
        argv.extend(["--aas-threads", str(int(at))])
    argv.extend(["--bspc", state["bspc"]])
    argv.extend(["--levelshot", state["levelshot"]])
    argv.extend(["--steamcmd", state["steamcmd"]])
    argv.extend(["--ffmpeg", state["ffmpeg"]])
    argv.extend(["--ql-pak", state["ql_pak"]])
    if state.get("yes_always"):
        argv.append("--yes-always")
    if state.get("force"):
        argv.append("--force")
    if state.get("no_aas"):
        argv.append("--no-aas")
    if state.get("optimize"):
        argv.append("--optimize")
    if state.get("dry_run"):
        argv.append("--dry-run")
    if state.get("hide_converted"):
        argv.append("--hide-converted")
    if state.get("skip_mapless"):
        argv.append("--skip-mapless")
    if state.get("verbose"):
        argv.append("--verbose")
    if state.get("show_skipped"):
        argv.append("--show-skipped")
    if state.get("time_stages"):
        argv.append("--time-stages")
    if state.get("no_aas_optimize"):
        argv.append("--no-aas-optimize")
    if state.get("aas_geometry_fast"):
        argv.append("--aas-geometry-fast")
    if state.get("aas_bspc_breadthfirst"):
        argv.append("--aas-bspc-breadthfirst")
    ws = state.get("workshop_list", [])
    if ws:
        argv.append("--workshop")
        argv.extend(ws)
    col_ids = state.get("collection_list", [])
    if col_ids:
        argv.append("--collection")
        argv.extend(col_ids)
    log_p = (state.get("log") or "").strip()
    if log_p:
        argv.extend(["--log", log_p])
    pos: list[str] = list(state.get("paths") or [])
    argv.extend(pos)
    argv.append("--no-progress")
    return argv


def build_cli_cmd(argv: list[str]) -> list[str]:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        cli_name = "qltoq3-cli.exe" if sys.platform == "win32" else "qltoq3-cli"
        cli_exe = exe_dir / cli_name
        if cli_exe.is_file():
            return [str(cli_exe)] + argv
    return [sys.executable, "-u", "-m", "qltoq3.cli"] + argv


def _popen_creationflags() -> int:
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


class WorkerThread(threading.Thread):
    def __init__(
        self,
        cmd: list[str],
        cwd: str,
        on_started: Callable[[subprocess.Popen[str]], None],
        on_progress: Callable[[int, int, str], None],
        on_phase: Callable[[str, int], None],
        on_action: Callable[[str], None],
        on_log_line: Callable[[str], None],
        on_done: Callable[[int], None],
        on_start_error: Callable[[str], None],
    ) -> None:
        super().__init__(daemon=True)
        self._cmd = cmd
        self._cwd = cwd
        self._on_started = on_started
        self._on_progress = on_progress
        self._on_phase = on_phase
        self._on_action = on_action
        self._on_log_line = on_log_line
        self._on_done = on_done
        self._on_start_error = on_start_error
        self._proc: subprocess.Popen[str] | None = None

    @property
    def proc(self) -> subprocess.Popen[str] | None:
        return self._proc

    def terminate(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()

    def run(self) -> None:
        try:
            child_env = os.environ.copy()
            child_env["QLTOQ3_NONINTERACTIVE"] = "1"
            self._proc = subprocess.Popen(
                self._cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=self._cwd,
                env=child_env,
                creationflags=_popen_creationflags(),
            )
            self._on_started(self._proc)
        except OSError as e:
            self._on_start_error(str(e))
            return

        assert self._proc and self._proc.stdout
        buf: list[str] = []

        def flush_buf() -> None:
            if not buf:
                return
            text = "".join(buf)
            buf.clear()
            self._on_log_line(text)

        for line in self._proc.stdout:
            raw = line.rstrip("\r\n")
            m = _PROGRESS_RE.match(raw)
            if m:
                flush_buf()
                self._on_progress(
                    int(m.group(1)),
                    int(m.group(2)),
                    m.group(3) if m.lastindex and m.lastindex >= 3 else "",
                )
                continue
            pm = _PHASE_RE.match(raw)
            if pm:
                flush_buf()
                self._on_phase(pm.group(1), int(pm.group(2)))
                continue
            am = _ACTION_RE.match(raw)
            if am:
                flush_buf()
                self._on_action(am.group(1))
                continue
            if not strip_ansi(raw).strip():
                continue
            buf.append(line)
            if len(buf) >= 32 or sum(len(x) for x in buf) > 12000:
                flush_buf()

        flush_buf()
        self._on_done(self._proc.wait())
