"""customtkinter gui: dark + orange accent."""

from __future__ import annotations

import ctypes
import os
import re
import subprocess
import sys
import tempfile
import time
import webbrowser
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import END, filedialog, messagebox
from typing import Any, Callable

import customtkinter as ctk

from .cli_parse import extract_steam_id
from .config import (
    default_gui_state,
    load_gui_state,
    merge_gui_state,
    save_gui_state,
)
from .constants import bundled_dir, repo_root
from . import __version__
from .l10n import default_lang_from_env, set_lang, tr
from .progress import format_elapsed as _format_elapsed_sec
from .runner import WorkerThread, build_argv, build_cli_cmd
from .tempdirs import find_stale_temp_dirs, remove_temp_dirs
from .ui.tabs import (
    DependenciesTab,
    LogsTab,
    SettingsTab,
    SourcesTab,
    UpdatesTab,
)
from .updater import (
    ReleaseInfo,
    download_file,
    fetch_latest_release,
    is_installed_mode,
    is_newer_version,
    read_sha256_from_file,
    verify_sha256,
)

ACCENT = "#D97800"
ACCENT_HOVER = "#B85F00"


PANEL = "#1e1e1e"
LIST_BG = "#2b2b2b"
SEG_UNSEL = "#3a3a3a"
SEG_UNSEL_HOVER = "#444444"
SIDEBAR_BG = "#151515"
BTN_GRAY = "#333333"
BTN_GRAY_HOVER = "#444444"

_ICO_RM = "\ue74d"
_ICO_CLR = "\ue75c"
_ICO_HOME = "\ue80f"
_ICO_SETTINGS = "\ue713"
_ICO_TOOLS = "\ue7ad"
_ICO_LOG = "\ue9d9"
_ICO_GLOBE = "\ue774"
_ICO_PLAY = "\ue768"
_ICO_PLUS = "\ue710"
_ICO_FOLDER = "\ue8b7"
_ICO_STOP = "\ue71a"
_ICO_OPEN = "\ue8a7"

_SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
_SPINNER_MS = 90

CHK_DEF: list[tuple[str, str]] = [
    ("yes_always", "gui.opt.yes_always"),
    ("force", "gui.opt.force"),
    ("no_aas", "gui.opt.no_aas"),
    ("optimize", "gui.opt.optimize"),
    ("dry_run", "gui.opt.dry_run"),
    ("hide_converted", "gui.opt.hide_converted"),
    ("skip_mapless", "gui.opt.skip_mapless"),
    ("verbose", "gui.opt.verbose"),
    ("show_skipped", "gui.opt.show_skipped"),
    ("time_stages", "gui.opt.time_stages"),
    ("no_aas_optimize", "gui.opt.no_aas_optimize"),
    ("aas_geometry_fast", "gui.opt.aas_geometry_fast"),
    ("aas_bspc_breadthfirst", "gui.opt.aas_bspc_breadthfirst"),
]

_TOOL_STATUS_DEBOUNCE_MS = 320
_TOOL_DOWNLOAD_URLS = {
    "steamcmd": "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip",
    "ffmpeg": "https://ffmpeg.org/download.html#build-windows",
}


def split_tokens(s: str) -> list[str]:
    return [t for t in re.split(r"[\s,]+", (s or "").strip()) if t]


def _runtime_root_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(repo_root()).resolve()


def _runtime_bundled_dir(runtime_root: Path) -> Path:
    bundled = runtime_root / "bundled"
    if bundled.is_dir():
        return bundled
    return Path(bundled_dir()).resolve()


def _safe_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _as_str_list(v: Any) -> list[str]:
    if not isinstance(v, list):
        return []
    return [str(x) for x in v]


def _ico_font(size: int = 16) -> ctk.CTkFont | None:
    fams = tkfont.families()
    target = ""
    for fam in ("Segoe MDL2 Assets", "Segoe Fluent Icons", "Segoe UI Symbol"):
        if fam in fams:
            target = fam
            break
    if target:
        return ctk.CTkFont(family=target, size=size)
    return None


def _bind_tip(w: Any, text_fn: Callable[[], str]) -> None:
    tw: list[tk.Toplevel | None] = [None]

    def leave(_: Any = None) -> None:
        if tw[0] is not None:
            tw[0].destroy()
            tw[0] = None

    def enter(_: Any = None) -> None:
        leave()
        t = tk.Toplevel(w)
        tw[0] = t
        t.wm_overrideredirect(True)
        t.attributes("-topmost", True)
        try:
            x = w.winfo_rootx() + 12
            y = w.winfo_rooty() + w.winfo_height() + 4
            t.geometry(f"+{x}+{y}")
        except tk.TclError:
            return
        body = text_fn()
        lbl = tk.Label(
            t,
            text=body,
            bg="#2d2d2d",
            fg="#f0f0f0",
            font=("segoe ui", 10),
            padx=8,
            pady=4,
            justify="left",
            wraplength=250,
        )
        lbl.pack()

    w.bind("<Enter>", enter)
    w.bind("<Leave>", leave)


def _png_to_temp_ico(png: Path) -> Path | None:
    try:
        from PIL import Image

        im = Image.open(png)
        fd, out = tempfile.mkstemp(suffix=".ico")
        os.close(fd)
        out_path = Path(out)
        try:
            im.save(
                str(out_path),
                format="ICO",
                sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)],
            )
        except Exception:
            im.save(str(out_path), format="ICO")
        return out_path
    except Exception:
        return None


def _apply_qltoq3_window_icon(app: ctk.CTk, bd: str) -> None:
    p = Path(bd)
    logo_png = p / "logo.png"
    logo_ico = p / "logo.ico"
    app._temp_ico_path = None  # type: ignore[attr-defined]
    if sys.platform == "win32":
        ico: Path | None = None
        if logo_ico.is_file():
            ico = logo_ico
        elif logo_png.is_file():
            ico = _png_to_temp_ico(logo_png)
            if ico is not None:
                app._temp_ico_path = ico  # type: ignore[attr-defined]
        ok = False
        if ico is not None:
            try:
                app.iconbitmap(default=str(ico.resolve()))
                ok = True
            except tk.TclError:
                ok = False
        if not ok and logo_png.is_file():
            try:
                app._app_icon = tk.PhotoImage(file=str(logo_png))
                app.wm_iconphoto(True, app._app_icon)
            except tk.TclError:
                pass
        return
    if logo_png.is_file():
        try:
            app._app_icon = tk.PhotoImage(file=str(logo_png))
            app.wm_iconphoto(True, app._app_icon)
        except tk.TclError:
            pass


class QlToQ3App(ctk.CTk):
    _dim_debounce_ms = 150

    def __init__(self) -> None:
        super().__init__()
        self._dim_after_id: str | None = None
        self._last_dim: tuple[int, int] = (0, 0)
        self._runtime_root = _runtime_root_dir()
        bd = str(_runtime_bundled_dir(self._runtime_root))
        _apply_qltoq3_window_icon(self, bd)
        root = str(self._runtime_root)
        self._bd = bd
        self._repo_root = root
        self._running = False
        self._user_stopped = False
        self._proc: subprocess.Popen[str] | None = None
        self._worker: WorkerThread | None = None
        self._spinner_after_id: str | None = None
        self._spinner_idx = 0
        self._run_started_t: float | None = None
        self._elapsed_after_id: str | None = None
        self._stop_elapsed_snapshot: float | None = None
        self._latest_known_version = ""
        self._pending_update_installer: Path | None = None
        self._pending_update_version = ""
        self._installed_mode = is_installed_mode(Path(sys.executable))
        init_lang = default_lang_from_env()
        if init_lang not in ("en", "ru"):
            init_lang = "en"
        set_lang(init_lang)

        self.title(tr("gui.title"))
        self.geometry("1100x850")
        self.configure(fg_color=PANEL)
        self.minsize(850, 650)

        # Fonts
        self._f_ico_btn = _ico_font(20)
        self._f_ico_small = _ico_font(16)
        self._f_ico_globe = _ico_font(16)

        # ui state
        self._lang_labels: list[tuple[ctk.CTkLabel, str]] = []
        self._lang_buttons: list[tuple[ctk.CTkButton, str]] = []
        self._chk: dict[str, tuple[ctk.CTkCheckBox, str]] = {}
        self._num: dict[str, ctk.CTkEntry] = {}
        self._path: dict[str, ctk.CTkEntry] = {}
        self._path_browse_btns: list[ctk.CTkButton] = []
        self._path_status_dots: dict[str, ctk.CTkLabel] = {}
        self._path_status_msgs: dict[str, str] = {}
        self._path_status_after: dict[str, str] = {}

        # layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # sidebar
        self.sidebar = ctk.CTkFrame(
            self, corner_radius=0, fg_color=SIDEBAR_BG, width=200
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        self._nav_sources = self._mk_nav_btn(0, tr("gui.tab_sources"), self._show_home)
        self._nav_sources.grid(row=1, column=0, sticky="ew", padx=10, pady=2)
        self._nav_settings = self._mk_nav_btn(
            1, tr("gui.tab_settings"), self._show_settings
        )
        self._nav_settings.grid(row=2, column=0, sticky="ew", padx=10, pady=2)
        self._nav_tools = self._mk_nav_btn(
            2, tr("gui.tab_dependencies"), self._show_tools
        )
        self._nav_tools.grid(row=3, column=0, sticky="ew", padx=10, pady=2)
        self._nav_updates = self._mk_nav_btn(3, tr("gui.tab_updates"), self._show_updates)
        self._nav_updates.grid(row=4, column=0, sticky="ew", padx=10, pady=2)
        self._nav_logs = self._mk_nav_btn(4, tr("gui.tab_logs"), self._show_log_tab)
        self._nav_logs.grid(row=5, column=0, sticky="ew", padx=10, pady=2)

        # bottom sidebar (lang)
        self._lang_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self._lang_frame.grid(row=7, column=0, padx=10, pady=20, sticky="ew")
        self._lang_combo = ctk.CTkComboBox(
            self._lang_frame,
            values=["en", "ru"],
            width=100,
            command=self._on_lang,
            fg_color=LIST_BG,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
        )
        self._lang_combo.set(init_lang)
        self._lang_combo.pack(side="right")
        self._lang_icon = ctk.CTkLabel(
            self._lang_frame,
            text=_ICO_GLOBE if self._f_ico_globe else "🌐",
            font=self._f_ico_globe,
        )
        self._lang_icon.pack(side="left", padx=(5, 5))

        # right frames
        self.home_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.settings_frame = ctk.CTkFrame(
            self, corner_radius=0, fg_color="transparent"
        )
        self.settings_frame.grid_columnconfigure(0, weight=1)
        self.settings_frame.grid_rowconfigure(0, weight=1)
        self.settings_scroll = ctk.CTkScrollableFrame(
            self.settings_frame, fg_color="transparent", corner_radius=0
        )
        self.settings_scroll.grid(row=0, column=0, sticky="nsew")
        self.tools_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.updates_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.log_tab_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        self.sources_tab = SourcesTab(self)
        self.settings_tab = SettingsTab(self)
        self.dependencies_tab = DependenciesTab(self)
        self.updates_tab = UpdatesTab(self)
        self.logs_tab = LogsTab(self)
        self.sources_tab.build()
        self.settings_tab.build()
        self.dependencies_tab.build()
        self.updates_tab.build()
        self.logs_tab.build()

        # status & run bar
        self.bottom_bar = ctk.CTkFrame(self, fg_color=PANEL)
        self.bottom_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)

        prog_wrap = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")
        prog_wrap.pack(fill="x", padx=20, pady=(8, 2))
        prog_section_row = ctk.CTkFrame(prog_wrap, fg_color="transparent")
        prog_section_row.pack(fill="x", anchor="w", pady=(0, 1))
        self._lab_progress_section = ctk.CTkLabel(
            prog_section_row,
            text=tr("gui.section_activity"),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#888888",
            anchor="w",
        )
        self._lab_progress_section.pack(side="left", anchor="w")
        self._lbl_run_elapsed = ctk.CTkLabel(
            prog_section_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#666666",
            anchor="e",
        )
        self._lbl_run_elapsed.pack(side="right")
        self._lang_labels.append((self._lab_progress_section, "gui.section_activity"))
        self._progress = ctk.CTkProgressBar(
            prog_wrap, progress_color=ACCENT, fg_color="#333333", height=6
        )
        self._progress.pack(fill="x", pady=(0, 2))
        self._progress.set(0)
        prog_detail_row = ctk.CTkFrame(prog_wrap, fg_color="transparent")
        prog_detail_row.pack(fill="x", anchor="w", pady=(0, 0))
        self._lbl_spinner = ctk.CTkLabel(
            prog_detail_row,
            text="",
            width=18,
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=ACCENT,
            padx=0,
            pady=0,
        )
        self._lbl_spinner.pack(side="left", padx=(0, 0))
        self._lbl_progress_detail = ctk.CTkLabel(
            prog_detail_row,
            text="",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color="#bbbbbb",
            padx=0,
            pady=0,
        )
        self._lbl_progress_detail.pack(side="left", fill="x", expand=True)
        self._lbl_progress_action = ctk.CTkLabel(
            prog_wrap,
            text="",
            anchor="w",
            font=ctk.CTkFont(size=10),
            text_color="#888888",
            padx=0,
            pady=0,
        )
        self._lbl_progress_action.pack(fill="x", anchor="w", pady=(0, 0))

        run_inner = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")
        run_inner.pack(fill="x", padx=20, pady=(4, 12))

        self._btn_run = ctk.CTkButton(
            run_inner,
            text=_ICO_PLAY if self._f_ico_btn else tr("gui.run"),
            font=(
                self._f_ico_btn
                if self._f_ico_btn
                else ctk.CTkFont(size=15, weight="bold")
            ),
            command=self._run,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            width=60,
            height=36,
        )
        self._btn_run.pack(side="left", padx=(0, 10))
        _bind_tip(self._btn_run, lambda: tr("gui.run"))

        self._btn_stop = ctk.CTkButton(
            run_inner,
            text=_ICO_STOP if self._f_ico_btn else tr("gui.stop"),
            font=(
                self._f_ico_btn
                if self._f_ico_btn
                else ctk.CTkFont(size=15, weight="bold")
            ),
            command=self._stop,
            fg_color="#444444",
            hover_color="#555555",
            width=60,
            height=36,
            state="disabled",
        )
        self._btn_stop.pack(side="left", padx=(0, 15))
        _bind_tip(self._btn_stop, lambda: tr("gui.stop"))

        self._credit = ctk.CTkLabel(
            run_inner,
            text=tr("gui.credit"),
            text_color=ACCENT,
            font=ctk.CTkFont(size=12),
            cursor="hand2",
        )
        self._credit.pack(side="right", padx=(10, 0))
        self._credit.bind("<Button-1>", lambda e: self._open_credit())
        self._credit.bind(
            "<Enter>", lambda e: self._credit.configure(text_color=ACCENT_HOVER)
        )
        self._credit.bind(
            "<Leave>", lambda e: self._credit.configure(text_color=ACCENT)
        )

        self._status = ctk.CTkLabel(
            run_inner, text="", text_color="#aaaaaa", font=ctk.CTkFont(size=13)
        )
        self._status.pack(side="right", padx=10)

        self._show_home()
        self._load_state()
        self._offer_stale_temp_cleanup()
        self._start_update_check()

        self.bind("<Configure>", self._update_dimensions_event)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _update_dimensions_event(self, event: Any = None) -> None:
        if event.widget != self:
            return
        new_dim = (event.width, event.height)
        if new_dim == self._last_dim:
            return
        self._last_dim = new_dim
        if self._dim_after_id is not None:
            try:
                self.after_cancel(self._dim_after_id)
            except Exception:
                pass
        self._dim_after_id = self.after(
            self._dim_debounce_ms, self._flush_update_dimensions, event
        )

    def _flush_update_dimensions(self, event: Any = None) -> None:
        self._dim_after_id = None
        try:
            super()._update_dimensions_event(event)
        except Exception:
            pass

    def _mk_nav_btn(self, idx: int, text: str, cmd: Callable) -> ctk.CTkButton:
        keys = [
            "gui.tab_sources",
            "gui.tab_settings",
            "gui.tab_dependencies",
            "gui.tab_updates",
            "gui.tab_logs",
        ]
        btn = ctk.CTkButton(
            self.sidebar,
            text=f"  {text}",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            height=40,
            command=cmd,
        )
        self._lang_buttons.append((btn, keys[idx]))
        return btn

    def _select_nav(self, btn: ctk.CTkButton) -> None:
        for b in [
            self._nav_sources,
            self._nav_settings,
            self._nav_tools,
            self._nav_updates,
            self._nav_logs,
        ]:
            b.configure(fg_color="transparent")
        btn.configure(fg_color=("gray75", "gray25"))

    def _show_home(self) -> None:
        self._select_nav(self._nav_sources)
        self.settings_frame.grid_forget()
        self.tools_frame.grid_forget()
        self.updates_frame.grid_forget()
        self.log_tab_frame.grid_forget()
        self.home_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def _show_settings(self) -> None:
        self._select_nav(self._nav_settings)
        self.home_frame.grid_forget()
        self.tools_frame.grid_forget()
        self.updates_frame.grid_forget()
        self.log_tab_frame.grid_forget()
        self.settings_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def _show_tools(self) -> None:
        self._select_nav(self._nav_tools)
        self.home_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.updates_frame.grid_forget()
        self.log_tab_frame.grid_forget()
        self._refresh_all_tool_path_status()
        self.tools_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def _show_updates(self) -> None:
        self._select_nav(self._nav_updates)
        self.home_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.tools_frame.grid_forget()
        self.log_tab_frame.grid_forget()
        self.updates_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def _show_log_tab(self) -> None:
        self._select_nav(self._nav_logs)
        self.home_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.tools_frame.grid_forget()
        self.updates_frame.grid_forget()
        self.log_tab_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def _setup_home(self) -> None:
        self.home_frame.grid_columnconfigure(0, weight=1)
        self.home_frame.grid_rowconfigure(2, weight=1)
        out_group = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        out_group.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self._mk_label(out_group, "gui.out_folder").pack(anchor="w", pady=(0, 5))
        out_inner = ctk.CTkFrame(out_group, fg_color="transparent")
        out_inner.pack(fill="x")
        self._out = ctk.CTkEntry(out_inner, height=32, fg_color=LIST_BG)
        self._out.insert(0, "q3")
        self._out.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._btn_out = self._mk_browse_btn(out_inner, self._browse_out)
        self._btn_out.pack(side="right")
        _bind_tip(self._btn_out, lambda: tr("gui.tip_browse_out"))
        self._btn_out_open = ctk.CTkButton(
            out_inner,
            text=_ICO_OPEN if self._f_ico_small else "↗",
            command=self._open_output_dir,
            fg_color=BTN_GRAY,
            hover_color=BTN_GRAY_HOVER,
            font=self._f_ico_small,
            height=32,
            width=40,
        )
        self._btn_out_open.pack(side="right", padx=(0, 8))
        _bind_tip(self._btn_out_open, lambda: tr("gui.open_output"))

        self._in_mode = ctk.CTkSegmentedButton(
            self.home_frame,
            values=[tr("gui.mode_local"), tr("gui.mode_steam")],
            command=self._on_in_mode,
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
            unselected_color=SEG_UNSEL,
            unselected_hover_color=SEG_UNSEL_HOVER,
        )
        self._in_mode.set(tr("gui.mode_local"))
        self._in_mode.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        self.local_frame = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        self.local_frame.grid(row=2, column=0, sticky="nsew")
        self.local_frame.grid_columnconfigure(0, weight=1)
        self.local_frame.grid_rowconfigure(1, weight=1)
        self._mk_label(self.local_frame, "gui.pk3_sources").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        lb_container = ctk.CTkFrame(self.local_frame, fg_color=LIST_BG, corner_radius=6)
        lb_container.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self._listbox = tk.Listbox(
            lb_container,
            height=10,
            bg=LIST_BG,
            fg="#e8e8e8",
            selectbackground=ACCENT,
            selectforeground="#101010",
            highlightthickness=0,
            borderwidth=0,
            font=("segoe ui", 11),
        )
        sb = tk.Scrollbar(
            lb_container, orient="vertical", command=self._listbox.yview, bg=LIST_BG
        )
        self._listbox.configure(yscrollcommand=sb.set)
        self._listbox.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        sb.pack(side="right", fill="y", padx=(0, 2), pady=5)
        self._listbox_empty = ctk.CTkLabel(
            lb_container,
            text=tr("gui.local_drop_hint"),
            text_color="#7f7f7f",
            anchor="center",
            justify="center",
        )
        self._listbox_empty.place(relx=0.5, rely=0.5, anchor="center")
        btn_row = ctk.CTkFrame(self.local_frame, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew")
        self._btn_add = ctk.CTkButton(
            btn_row,
            text=tr("gui.add_files"),
            command=self._add_files,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            width=130,
        )
        self._btn_add.pack(side="left", padx=(0, 10))
        _bind_tip(self._btn_add, lambda: tr("gui.tip_add_files"))
        self._btn_dir = ctk.CTkButton(
            btn_row,
            text=tr("gui.add_dir"),
            command=self._add_dir,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            width=130,
        )
        self._btn_dir.pack(side="left", padx=(0, 10))
        _bind_tip(self._btn_dir, lambda: tr("gui.tip_add_dir"))

        self._btn_rm = ctk.CTkButton(
            btn_row,
            text=_ICO_RM if self._f_ico_small else "rm",
            font=self._f_ico_small,
            width=40,
            height=32,
            command=self._remove_sel,
            fg_color=BTN_GRAY,
            hover_color=BTN_GRAY_HOVER,
        )
        self._btn_rm.pack(side="left", padx=(0, 6))
        _bind_tip(self._btn_rm, lambda: tr("gui.tip_remove"))
        self._btn_clear = ctk.CTkButton(
            btn_row,
            text=_ICO_CLR if self._f_ico_small else "clr",
            font=self._f_ico_small,
            width=40,
            height=32,
            command=self._clear_list,
            fg_color=BTN_GRAY,
            hover_color=BTN_GRAY_HOVER,
        )
        self._btn_clear.pack(side="left")
        _bind_tip(self._btn_clear, lambda: tr("gui.tip_clear"))
        self._refresh_local_placeholder()

        self.steam_frame = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        self.steam_frame.grid_columnconfigure((0, 1), weight=1)
        self.steam_frame.grid_rowconfigure(0, weight=1)
        ws_col = ctk.CTkFrame(self.steam_frame, fg_color="transparent")
        ws_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._mk_label(ws_col, "gui.workshop_ids").pack(anchor="w", pady=(0, 5))
        ws_add_row = ctk.CTkFrame(ws_col, fg_color="transparent")
        ws_add_row.pack(fill="x", pady=(0, 5))
        self._ws_entry = ctk.CTkEntry(
            ws_add_row, height=32, fg_color=LIST_BG, placeholder_text="id..."
        )
        self._ws_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._btn_ws_add = ctk.CTkButton(
            ws_add_row,
            text=_ICO_PLUS if self._f_ico_small else tr("gui.add"),
            font=self._f_ico_small,
            width=32,
            height=32,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=self._add_workshop,
        )
        self._btn_ws_add.pack(side="right")
        _bind_tip(self._btn_ws_add, lambda: tr("gui.add"))
        ws_lb_cont = ctk.CTkFrame(ws_col, fg_color=LIST_BG, corner_radius=6)
        ws_lb_cont.pack(fill="both", expand=True)
        self._ws_listbox = tk.Listbox(
            ws_lb_cont,
            bg=LIST_BG,
            fg="#e8e8e8",
            borderwidth=0,
            highlightthickness=0,
            font=("segoe ui", 11),
            height=8,
        )
        self._ws_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self._ws_listbox.bind("<Delete>", lambda _: self._remove_ws())
        ws_btn_row = ctk.CTkFrame(ws_col, fg_color="transparent")
        ws_btn_row.pack(fill="x", pady=(8, 0))
        self._btn_ws_rm = ctk.CTkButton(
            ws_btn_row,
            text=_ICO_RM if self._f_ico_small else "rm",
            font=self._f_ico_small,
            width=40,
            height=32,
            command=self._remove_ws,
            fg_color=BTN_GRAY,
            hover_color=BTN_GRAY_HOVER,
        )
        self._btn_ws_rm.pack(side="left", padx=(0, 6))
        _bind_tip(self._btn_ws_rm, lambda: tr("gui.tip_remove"))
        self._btn_ws_clr = ctk.CTkButton(
            ws_btn_row,
            text=_ICO_CLR if self._f_ico_small else "clr",
            font=self._f_ico_small,
            width=40,
            height=32,
            command=self._clear_ws_list,
            fg_color=BTN_GRAY,
            hover_color=BTN_GRAY_HOVER,
        )
        self._btn_ws_clr.pack(side="left")
        _bind_tip(self._btn_ws_clr, lambda: tr("gui.tip_clear"))

        col_col = ctk.CTkFrame(self.steam_frame, fg_color="transparent")
        col_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._mk_label(col_col, "gui.collection_ids").pack(anchor="w", pady=(0, 5))
        col_add_row = ctk.CTkFrame(col_col, fg_color="transparent")
        col_add_row.pack(fill="x", pady=(0, 5))
        self._col_entry = ctk.CTkEntry(
            col_add_row, height=32, fg_color=LIST_BG, placeholder_text="id..."
        )
        self._col_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._btn_col_add = ctk.CTkButton(
            col_add_row,
            text=_ICO_PLUS if self._f_ico_small else tr("gui.add"),
            font=self._f_ico_small,
            width=32,
            height=32,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=self._add_collection,
        )
        self._btn_col_add.pack(side="right")
        _bind_tip(self._btn_col_add, lambda: tr("gui.add"))
        col_lb_cont = ctk.CTkFrame(col_col, fg_color=LIST_BG, corner_radius=6)
        col_lb_cont.pack(fill="both", expand=True)
        self._col_listbox = tk.Listbox(
            col_lb_cont,
            bg=LIST_BG,
            fg="#e8e8e8",
            borderwidth=0,
            highlightthickness=0,
            font=("segoe ui", 11),
            height=8,
        )
        self._col_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self._col_listbox.bind("<Delete>", lambda _: self._remove_col())
        col_btn_row = ctk.CTkFrame(col_col, fg_color="transparent")
        col_btn_row.pack(fill="x", pady=(8, 0))
        self._btn_col_rm = ctk.CTkButton(
            col_btn_row,
            text=_ICO_RM if self._f_ico_small else "rm",
            font=self._f_ico_small,
            width=40,
            height=32,
            command=self._remove_col,
            fg_color=BTN_GRAY,
            hover_color=BTN_GRAY_HOVER,
        )
        self._btn_col_rm.pack(side="left", padx=(0, 6))
        _bind_tip(self._btn_col_rm, lambda: tr("gui.tip_remove"))
        self._btn_col_clr = ctk.CTkButton(
            col_btn_row,
            text=_ICO_CLR if self._f_ico_small else "clr",
            font=self._f_ico_small,
            width=40,
            height=32,
            command=self._clear_col_list,
            fg_color=BTN_GRAY,
            hover_color=BTN_GRAY_HOVER,
        )
        self._btn_col_clr.pack(side="left")
        _bind_tip(self._btn_col_clr, lambda: tr("gui.tip_clear"))

    def _setup_settings(self) -> None:
        sc = self.settings_scroll
        self._lab_beh = ctk.CTkLabel(
            sc, text=tr("gui.header_behavior").lower(), font=ctk.CTkFont(weight="bold")
        )
        self._lab_beh.pack(anchor="w", pady=(0, 15))
        cb_grid = ctk.CTkFrame(sc, fg_color="transparent")
        cb_grid.pack(fill="x", padx=10)
        for key, lk in CHK_DEF:
            cb = ctk.CTkCheckBox(
                cb_grid, text=tr(lk), fg_color=ACCENT, hover_color=ACCENT_HOVER
            )
            if hasattr(cb, "_label"):
                cb._label.configure(wraplength=560, justify="left")
            cb.pack(anchor="w", fill="x", pady=5)
            self._chk[key] = (cb, lk)
        row_bm = ctk.CTkFrame(sc, fg_color="transparent")
        row_bm.pack(fill="x", padx=25, pady=(5, 0))
        _lb = self._mk_label(row_bm, "gui.opt.bsp_patch")
        _lb.configure(wraplength=420, justify="left")
        _lb.pack(side="left", padx=(0, 15), fill="x", expand=True)
        self._bsp_patch = ctk.CTkComboBox(
            row_bm,
            values=["1", "2"],
            width=70,
            height=32,
            fg_color=LIST_BG,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
        )
        self._bsp_patch.set("1")
        self._bsp_patch.pack(side="right")
        sep = ctk.CTkFrame(sc, height=2, fg_color="#333333")
        sep.pack(fill="x", pady=25)
        self._lab_pool = ctk.CTkLabel(
            sc,
            text=tr("gui.header_parallelism").lower(),
            font=ctk.CTkFont(weight="bold"),
        )
        self._lab_pool.pack(anchor="w", pady=(0, 15))
        pf = ctk.CTkFrame(sc, fg_color="transparent")
        pf.pack(fill="x", padx=10)
        num_fields = [
            ("coworkers", "gui.num.coworkers", "3"),
            ("pool_max", "gui.num.pool_max", "96"),
            ("aas_timeout", "gui.num.aas_timeout", "90"),
            ("bspc_concurrent", "gui.num.bspc_concurrent", "1"),
        ]
        _num_h = 32
        for nk, lk, default in num_fields:
            row = ctk.CTkFrame(pf, fg_color="transparent")
            row.pack(fill="x", pady=6)
            lab = self._mk_label(row, lk)
            lab.configure(wraplength=420, justify="left")
            lab.pack(side="left", padx=(0, 15), fill="x", expand=True)
            e = ctk.CTkEntry(row, width=80, height=_num_h, fg_color=LIST_BG)
            e.insert(0, default)
            e.pack(side="right")
            self._num[nk] = e
        row_at = ctk.CTkFrame(pf, fg_color="transparent")
        row_at.pack(fill="x", pady=(10, 0))
        _la = self._mk_label(row_at, "gui.num.aas_threads")
        _la.configure(wraplength=420, justify="left")
        _la.pack(side="left", padx=(0, 15), fill="x", expand=True)
        self._aas_threads = ctk.CTkEntry(
            row_at,
            width=80,
            height=_num_h,
            fg_color=LIST_BG,
            placeholder_text=tr("gui.placeholder_auto"),
        )
        self._aas_threads.pack(side="right")
        self._btn_reset = ctk.CTkButton(
            sc,
            text=tr("gui.reset"),
            command=self._reset_gui_defaults,
            fg_color=BTN_GRAY,
            hover_color=BTN_GRAY_HOVER,
            height=36,
        )
        self._btn_reset.pack(anchor="w", padx=10, pady=(28, 10))

    def _setup_tools(self, bd: str, root: str) -> None:
        self.tools_frame.grid_columnconfigure(0, weight=1)
        sc = ctk.CTkScrollableFrame(self.tools_frame, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        tool_fields = [
            ("bspc", "gui.path.bspc", os.path.join(bd, "bspc.exe")),
            ("levelshot", "gui.path.levelshot", os.path.join(bd, "levelshot.png")),
            ("steamcmd", "gui.path.steamcmd", r"c:\steamcmd\steamcmd.exe"),
            ("ffmpeg", "gui.path.ffmpeg", "ffmpeg"),
            ("ql_pak", "gui.path.ql_pak", os.path.join(root, "ql_baseq3", "pak00.pk3")),
        ]
        for nk, lk, default in tool_fields:
            self._mk_label(sc, lk).pack(anchor="w", pady=(15, 5))
            if nk in _TOOL_DOWNLOAD_URLS:
                hint_key = (
                    "gui.dep_hint_steamcmd"
                    if nk == "steamcmd"
                    else "gui.dep_hint_ffmpeg"
                )
                url = _TOOL_DOWNLOAD_URLS[nk]
                hint = ctk.CTkLabel(
                    sc,
                    text=tr(hint_key),
                    text_color=ACCENT,
                    cursor="hand2",
                    font=ctk.CTkFont(size=11),
                )
                hint.pack(anchor="w", pady=(0, 4))
                self._lang_labels.append((hint, hint_key))
                hint.bind("<Button-1>", lambda _e, link=url: webbrowser.open(link))
                hint.bind(
                    "<Enter>", lambda _e, w=hint: w.configure(text_color=ACCENT_HOVER)
                )
                hint.bind("<Leave>", lambda _e, w=hint: w.configure(text_color=ACCENT))
            row = ctk.CTkFrame(sc, fg_color="transparent")
            row.pack(fill="x", pady=(0, 8), padx=(0, 10))
            e = ctk.CTkEntry(row, fg_color=LIST_BG, height=32)
            e.insert(0, default)
            e.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self._path[nk] = e
            e.bind("<KeyRelease>", lambda _ev, k=nk: self._schedule_tool_path_status(k))
            e.bind("<FocusOut>", lambda _ev, k=nk: self._refresh_tool_path_status(k))
            bb = self._mk_browse_btn(row, lambda k=nk: self._browse_tool(k))
            bb.pack(side="right")
            self._path_browse_btns.append(bb)
            _bind_tip(bb, lambda: tr("gui.browse"))
            dot = ctk.CTkLabel(row, text="●", width=16, text_color="#808080")
            dot.pack(side="right", padx=(0, 8))
            self._path_status_dots[nk] = dot
            self._path_status_msgs[nk] = tr("gui.path_status_empty")
            _bind_tip(dot, lambda k=nk: self._path_status_msgs.get(k, ""))
        self._refresh_all_tool_path_status()

    def _setup_updates(self) -> None:
        self.updates_frame.grid_columnconfigure(0, weight=1)
        self.updates_frame.grid_rowconfigure(0, weight=1)
        sc = ctk.CTkScrollableFrame(
            self.updates_frame, fg_color="transparent", corner_radius=0
        )
        sc.grid(row=0, column=0, sticky="nsew")
        self._lab_update = ctk.CTkLabel(
            sc,
            text=tr("gui.header_updates").lower(),
            font=ctk.CTkFont(weight="bold"),
        )
        self._lab_update.pack(anchor="w", pady=(0, 15))
        self._lang_labels.append((self._lab_update, "gui.header_updates"))

        self._chk_update_wrap = ctk.CTkFrame(sc, fg_color="transparent")
        self._chk_update_wrap.pack(fill="x", padx=10, pady=(0, 10))
        for key, lk in (
            ("check_updates_on_start", "gui.opt.check_updates_on_start"),
            ("auto_download_update", "gui.opt.auto_download_update"),
        ):
            cb = ctk.CTkCheckBox(
                self._chk_update_wrap, text=tr(lk), fg_color=ACCENT, hover_color=ACCENT_HOVER
            )
            if hasattr(cb, "_label"):
                cb._label.configure(wraplength=560, justify="left")
            cb.pack(anchor="w", fill="x", pady=5)
            self._chk[key] = (cb, lk)

        self._btn_check_updates = ctk.CTkButton(
            sc,
            text=tr("gui.update_check_now"),
            command=self._check_updates_now,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            width=210,
            height=34,
        )
        self._btn_check_updates.pack(anchor="w", padx=10, pady=(0, 8))
        self._btn_update_now = ctk.CTkButton(
            sc,
            text=tr("gui.update_install_now"),
            command=self._install_update_now,
            fg_color=BTN_GRAY,
            hover_color=BTN_GRAY_HOVER,
            width=210,
            height=34,
            state="disabled",
        )
        self._btn_update_now.pack(anchor="w", padx=10, pady=(0, 14))

        ver_wrap = ctk.CTkFrame(sc, fg_color="transparent")
        ver_wrap.pack(fill="x", padx=10, pady=(0, 10))
        ver_wrap.grid_columnconfigure(1, weight=1)
        self._lab_update_current_k = ctk.CTkLabel(
            ver_wrap, text=tr("gui.update_current_label"), text_color="#aaaaaa"
        )
        self._lab_update_current_k.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._lang_labels.append((self._lab_update_current_k, "gui.update_current_label"))
        self._lab_update_current = ctk.CTkLabel(
            ver_wrap, text=__version__, text_color="#aaaaaa", anchor="w"
        )
        self._lab_update_current.grid(row=0, column=1, sticky="w")
        self._lab_update_latest_k = ctk.CTkLabel(
            ver_wrap, text=tr("gui.update_latest_label"), text_color="#aaaaaa"
        )
        self._lab_update_latest_k.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        self._lang_labels.append((self._lab_update_latest_k, "gui.update_latest_label"))
        self._lab_update_latest = ctk.CTkLabel(
            ver_wrap, text="-", text_color="#aaaaaa", anchor="w"
        )
        self._lab_update_latest.grid(row=1, column=1, sticky="w", pady=(4, 0))
        self._refresh_latest_version_label()
        self._refresh_update_install_button()

    def _validate_tool_path(self, key: str) -> tuple[str, str]:
        raw = self._path[key].get().strip()
        if not raw:
            return "#808080", tr("gui.path_status_empty")
        p = Path(raw).expanduser()
        if not p.exists():
            return "#ff5555", tr("gui.path_status_missing")
        if p.is_dir():
            return "#ffb347", tr("gui.path_status_need_file")
        return "#55cc66", tr("gui.path_status_ok")

    def _refresh_tool_path_status(self, key: str) -> None:
        after_id = self._path_status_after.pop(key, None)
        if after_id:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        color, msg = self._validate_tool_path(key)
        dot = self._path_status_dots.get(key)
        if dot is not None:
            dot.configure(text_color=color)
        self._path_status_msgs[key] = msg

    def _schedule_tool_path_status(self, key: str) -> None:
        prev = self._path_status_after.get(key)
        if prev:
            try:
                self.after_cancel(prev)
            except Exception:
                pass
        self._path_status_after[key] = self.after(
            _TOOL_STATUS_DEBOUNCE_MS,
            lambda k=key: self._refresh_tool_path_status(k),
        )

    def _refresh_all_tool_path_status(self) -> None:
        for key in self._path:
            self._refresh_tool_path_status(key)

    def _browse_tool(self, key: str) -> None:
        e = self._path[key]
        ft = [("All", "*.*")]
        if key == "bspc":
            ft = [("bspc", "*.exe"), ("All", "*.*")]
        elif key == "levelshot":
            ft = [
                ("png", "*.png"),
                ("jpeg", "*.jpg"),
                ("jpeg", "*.jpeg"),
                ("tga", "*.tga"),
                ("All", "*.*"),
            ]
        elif key == "steamcmd":
            ft = [("steamcmd", "*.exe"), ("All", "*.*")]
        elif key == "ffmpeg":
            ft = [("exe", "*.exe"), ("All", "*.*")]
        elif key == "ql_pak":
            ft = [("pk3", "*.pk3"), ("All", "*.*")]
        p = filedialog.askopenfilename(filetypes=ft)
        if p:
            e.delete(0, "end")
            e.insert(0, p)
            self._refresh_tool_path_status(key)

    def _setup_log_tab(self) -> None:
        self.log_tab_frame.grid_columnconfigure(0, weight=1)
        self.log_tab_frame.grid_rowconfigure(1, weight=1)
        adv_group = ctk.CTkFrame(self.log_tab_frame, fg_color="transparent")
        adv_group.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self._mk_label(adv_group, "gui.extra_log").pack(side="left", padx=(0, 10))
        self._log_path = ctk.CTkEntry(
            adv_group, fg_color=LIST_BG, placeholder_text=tr("gui.log_path_ph")
        )
        self._log_path.pack(side="left", fill="x", expand=True)
        log_group = ctk.CTkFrame(self.log_tab_frame, fg_color="transparent")
        log_group.grid(row=1, column=0, sticky="nsew")
        log_group.grid_columnconfigure(0, weight=1)
        log_group.grid_rowconfigure(1, weight=1)
        self._mk_label(log_group, "gui.log").grid(row=0, column=0, sticky="w")
        self._log_box = ctk.CTkTextbox(
            log_group, fg_color=LIST_BG, font=("consolas", 11)
        )
        self._log_box.grid(row=1, column=0, sticky="nsew", pady=(5, 10))
        self._log_box.configure(state="disabled")
        self._log_autoscroll = True
        self._log_box.bind("<MouseWheel>", self._on_log_scroll)
        self._log_box.bind("<Button-4>", self._on_log_scroll)
        self._log_box.bind("<Button-5>", self._on_log_scroll)
        btn_log = ctk.CTkFrame(log_group, fg_color="transparent")
        btn_log.grid(row=2, column=0, sticky="ew")
        self._btn_log_copy = ctk.CTkButton(
            btn_log,
            text=tr("gui.copy_log"),
            command=self._copy_log,
            fg_color="#333333",
            hover_color="#444444",
            width=140,
        )
        self._btn_log_copy.pack(side="left", padx=(0, 8))
        self._btn_log_save = ctk.CTkButton(
            btn_log,
            text=tr("gui.save_log"),
            command=self._save_log_to_file,
            fg_color="#333333",
            hover_color="#444444",
            width=160,
        )
        self._btn_log_save.pack(side="left")
        self._btn_log_clear = ctk.CTkButton(
            btn_log,
            text=tr("gui.clear_log"),
            command=self._clear_log,
            fg_color="#333333",
            hover_color="#444444",
            width=120,
        )
        self._btn_log_clear.pack(side="right")

    def _mk_browse_btn(self, parent: Any, command: Callable[[], None]) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=_ICO_FOLDER if self._f_ico_small else tr("gui.browse"),
            font=self._f_ico_small,
            width=40,
            height=32,
            command=command,
            fg_color=BTN_GRAY,
            hover_color=BTN_GRAY_HOVER,
        )

    def _refresh_browse_btns(self) -> None:
        self._btn_out.configure(
            text=_ICO_FOLDER if self._f_ico_small else tr("gui.browse"),
            font=self._f_ico_small,
        )
        for b in self._path_browse_btns:
            b.configure(
                text=_ICO_FOLDER if self._f_ico_small else tr("gui.browse"),
                font=self._f_ico_small,
            )

    def _mk_label(self, parent: Any, key: str) -> ctk.CTkLabel:
        lab = ctk.CTkLabel(parent, text=tr(key))
        self._lang_labels.append((lab, key))
        return lab

    def _on_lang(self, choice: str) -> None:
        set_lang(choice if choice in ("en", "ru") else "en")
        for lab, key in self._lang_labels:
            lab.configure(text=tr(key))
        for btn, key in self._lang_buttons:
            btn.configure(text=f"  {tr(key)}")
        self.title(tr("gui.title"))
        self._credit.configure(text=tr("gui.credit"))
        self._btn_add.configure(text=tr("gui.add_files"))
        self._btn_dir.configure(text=tr("gui.add_dir"))
        self._btn_ws_add.configure(
            text=_ICO_PLUS if self._f_ico_small else tr("gui.add")
        )
        self._btn_col_add.configure(
            text=_ICO_PLUS if self._f_ico_small else tr("gui.add")
        )
        self._refresh_browse_btns()
        self._btn_out_open.configure(
            text=_ICO_OPEN if self._f_ico_small else "↗",
            font=self._f_ico_small,
        )
        self._listbox_empty.configure(text=tr("gui.local_drop_hint"))
        self._btn_stop.configure(text=_ICO_STOP if self._f_ico_btn else tr("gui.stop"))
        self._btn_log_copy.configure(text=tr("gui.copy_log"))
        self._btn_log_save.configure(text=tr("gui.save_log"))
        self._btn_log_clear.configure(text=tr("gui.clear_log"))
        self._btn_reset.configure(text=tr("gui.reset"))
        for _k, (cb, lk) in self._chk.items():
            cb.configure(text=tr(lk))
        self._in_mode.configure(values=[tr("gui.mode_local"), tr("gui.mode_steam")])
        self._lab_beh.configure(text=tr("gui.header_behavior").lower())
        self._lab_pool.configure(text=tr("gui.header_parallelism").lower())
        self._aas_threads.configure(placeholder_text=tr("gui.placeholder_auto"))
        self._log_path.configure(placeholder_text=tr("gui.log_path_ph"))
        self._btn_run.configure(text=_ICO_PLAY if self._f_ico_btn else tr("gui.run"))
        self._btn_check_updates.configure(text=tr("gui.update_check_now"))
        self._btn_update_now.configure(text=tr("gui.update_install_now"))
        self._lab_update_current.configure(text=__version__)
        self._refresh_latest_version_label()
        self._refresh_update_install_button()
        self._refresh_all_tool_path_status()
        self._lang_icon.configure(text=_ICO_GLOBE if self._f_ico_globe else "🌐")

    def _on_in_mode(self, choice: str) -> None:
        if choice == tr("gui.mode_local"):
            self.steam_frame.grid_forget()
            self.local_frame.grid(row=2, column=0, sticky="nsew")
        else:
            self.local_frame.grid_forget()
            self.steam_frame.grid(row=2, column=0, sticky="nsew")

    def _add_workshop(self) -> None:
        tokens = split_tokens(self._ws_entry.get())
        if not tokens:
            return
        existing = set(map(str, self._ws_listbox.get(0, END)))
        added = 0
        for tok in tokens:
            sid = extract_steam_id(tok)
            if sid and sid not in existing:
                self._ws_listbox.insert(END, sid)
                existing.add(sid)
                added += 1
        if added > 0:
            self._ws_entry.delete(0, END)
        else:
            self._status.configure(text=tr("gui.ws_id_invalid"), text_color="#ff5555")

    def _remove_ws(self) -> None:
        for i in reversed(self._ws_listbox.curselection()):
            self._ws_listbox.delete(i)

    def _clear_ws_list(self) -> None:
        self._ws_listbox.delete(0, END)

    def _add_collection(self) -> None:
        tokens = split_tokens(self._col_entry.get())
        if not tokens:
            return
        existing = set(map(str, self._col_listbox.get(0, END)))
        added = 0
        for tok in tokens:
            sid = extract_steam_id(tok)
            if sid and sid not in existing:
                self._col_listbox.insert(END, sid)
                existing.add(sid)
                added += 1
        if added > 0:
            self._col_entry.delete(0, END)
        else:
            self._status.configure(text=tr("gui.col_id_invalid"), text_color="#ff5555")

    def _offer_stale_temp_cleanup(self) -> None:
        stale = find_stale_temp_dirs()
        if not stale:
            return
        do_remove = messagebox.askyesno(
            tr("gui.tmp_found_title"),
            tr("gui.tmp_found_msg", n=len(stale)),
        )
        if not do_remove:
            self._status.configure(text=tr("gui.tmp_kept"), text_color="#aaaaaa")
            return
        removed, failed = remove_temp_dirs(stale)
        if failed:
            self._status.configure(
                text=tr("gui.tmp_remove_failed", n=failed), text_color="#ff5555"
            )
            return
        self._status.configure(text=tr("gui.tmp_removed", n=removed), text_color="#aaaaaa")

    def _refresh_latest_version_label(self) -> None:
        shown = self._latest_known_version or "-"
        self._lab_update_latest.configure(text=shown)

    def _refresh_update_install_button(self) -> None:
        ready = bool(
            self._pending_update_installer
            and self._pending_update_installer.is_file()
            and self._pending_update_version
        )
        self._btn_update_now.configure(state=("normal" if ready else "disabled"))

    def _install_update_now(self) -> None:
        if (
            not self._pending_update_installer
            or not self._pending_update_installer.is_file()
            or not self._pending_update_version
        ):
            self._status.configure(text=tr("gui.update_no_pending"), text_color="#aaaaaa")
            self._refresh_update_install_button()
            return
        self._status.configure(
            text=tr("gui.update_silent_start", latest=self._pending_update_version),
            text_color="#aaaaaa",
        )
        self._on_close()

    def _check_updates_now(self) -> None:
        self._status.configure(text=tr("gui.update_checking"), text_color="#aaaaaa")
        threading.Thread(
            target=self._update_check_worker,
            kwargs={"manual": True},
            daemon=True,
        ).start()

    def _start_update_check(self) -> None:
        cb = self._chk.get("check_updates_on_start")
        if not cb or cb[0].get() != 1:
            return
        threading.Thread(target=self._update_check_worker, daemon=True).start()

    def _update_check_worker(self, manual: bool = False) -> None:
        info = fetch_latest_release()
        if info is None:
            if manual:
                self.after(
                    0,
                    lambda: self._status.configure(
                        text=tr("gui.update_check_failed"), text_color="#ff5555"
                    ),
                )
            return
        self.after(0, self._on_update_info, info, manual)

    def _on_update_info(self, info: ReleaseInfo, manual: bool) -> None:
        self._latest_known_version = info.latest_version
        self._refresh_latest_version_label()
        if not is_newer_version(info.latest_version, __version__):
            if manual:
                self._status.configure(text=tr("gui.update_none"), text_color="#55ff55")
            return
        self._status.configure(
            text=tr("gui.update_available_status", latest=info.latest_version),
            text_color="#aaaaaa",
        )
        auto_cb = self._chk.get("auto_download_update")
        auto_enabled = bool(auto_cb and auto_cb[0].get() == 1)
        # Manual check should also prepare the installer so "install now"
        # becomes available without restarting the app.
        if auto_enabled or manual:
            if self._auto_update_flow(info):
                return
        self._notify_update_available(info)

    def _notify_update_available(self, info: ReleaseInfo) -> None:
        open_now = messagebox.askyesno(
            tr("gui.update_title"),
            tr(
                "gui.update_available_msg",
                current=__version__,
                latest=info.latest_version,
            ),
        )
        if open_now:
            webbrowser.open(info.asset_url or info.html_url)

    def _auto_update_flow(self, info: ReleaseInfo) -> bool:
        if not self._installed_mode:
            self._status.configure(
                text=tr("gui.update_auto_installed_only"),
                text_color="#aaaaaa",
            )
            return False
        if not info.asset_url or not info.asset_name or not info.sha256_url:
            self._status.configure(
                text=tr("gui.update_integrity_missing"),
                text_color="#ff5555",
            )
            return False
        threading.Thread(
            target=self._download_and_stage_update,
            args=(info,),
            daemon=True,
        ).start()
        return True

    def _download_and_stage_update(self, info: ReleaseInfo) -> None:
        installer_path = Path(tempfile.gettempdir()) / info.asset_name
        sha_path = installer_path.with_suffix(installer_path.suffix + ".sha256")
        try:
            download_file(info.asset_url, installer_path)
            download_file(info.sha256_url, sha_path)
            expected = read_sha256_from_file(sha_path)
            if not expected or not verify_sha256(installer_path, expected):
                self.after(
                    0,
                    lambda: self._status.configure(
                        text=tr("gui.update_integrity_failed"),
                        text_color="#ff5555",
                    ),
                )
                return
        except OSError:
            self.after(
                0,
                lambda: self._status.configure(
                    text=tr("gui.update_download_failed"), text_color="#ff5555"
                ),
            )
            return
        self.after(0, self._schedule_silent_update, info.latest_version, installer_path)

    def _schedule_silent_update(self, latest: str, installer_path: Path) -> None:
        self._pending_update_installer = installer_path
        self._pending_update_version = latest
        self._refresh_update_install_button()
        self._status.configure(
            text=tr("gui.update_deferred", latest=latest),
            text_color="#aaaaaa",
        )

    def _remove_col(self) -> None:
        for i in reversed(self._col_listbox.curselection()):
            self._col_listbox.delete(i)

    def _clear_col_list(self) -> None:
        self._col_listbox.delete(0, END)

    def _refresh_local_placeholder(self) -> None:
        if self._listbox.size() == 0:
            self._listbox_empty.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self._listbox_empty.place_forget()

    def _open_output_dir(self) -> None:
        raw = self._out.get().strip()
        if not raw:
            self._status.configure(text=tr("gui.err_output"), text_color="#ff5555")
            return
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p
        try:
            p = p.resolve(strict=False)
        except OSError:
            pass
        if not p.exists() or not p.is_dir():
            self._status.configure(text=tr("gui.out_retry_hint"), text_color="#ff5555")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(p))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except OSError as e:
            self._status.configure(
                text=tr("gui.open_output_failed", error=e), text_color="#ff5555"
            )

    def _browse_out(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self._out.delete(0, "end")
            self._out.insert(0, d)

    def _choose_output_dir(self, initial: Path | None = None) -> Path | None:
        title = tr("gui.out_pick_title")
        start_dir = str(initial) if initial and initial.exists() else os.getcwd()
        d = filedialog.askdirectory(title=title, initialdir=start_dir)
        if not d:
            return None
        p = Path(d).expanduser()
        try:
            p = p.resolve(strict=False)
        except OSError:
            pass
        self._out.delete(0, "end")
        self._out.insert(0, str(p))
        return p

    def _check_output_writable(self, out_dir: Path) -> str | None:
        probe = out_dir / f".qltoq3_write_test_{os.getpid()}_{int(time.time() * 1000)}.tmp"
        try:
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            probe.unlink(missing_ok=True)
            return None
        except OSError as e:
            return str(e)

    def _prepare_output_dir(self, raw_output: str) -> str | None:
        out_dir = Path(raw_output).expanduser()
        if not out_dir.is_absolute():
            out_dir = Path.cwd() / out_dir
        try:
            out_dir = out_dir.resolve(strict=False)
        except OSError:
            pass
        while True:
            if out_dir.exists() and not out_dir.is_dir():
                messagebox.showerror(
                    tr("gui.out_not_dir_title"),
                    tr("gui.out_not_dir_msg", path=out_dir),
                )
                chosen = self._choose_output_dir(out_dir.parent if out_dir.parent.exists() else None)
                if chosen is None:
                    self._status.configure(
                        text=tr("gui.out_canceled"),
                        text_color="#ff5555",
                    )
                    return None
                out_dir = chosen
                continue

            if not out_dir.exists():
                create_ok = messagebox.askyesno(
                    tr("gui.out_missing_title"),
                    tr("gui.out_missing_msg", path=out_dir),
                )
                if not create_ok:
                    self._status.configure(
                        text=tr("gui.out_canceled"),
                        text_color="#ff5555",
                    )
                    return None
                try:
                    out_dir.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    choose_other = messagebox.askyesno(
                        tr("gui.out_mkdir_fail_title"),
                        tr("gui.out_mkdir_fail_msg", path=out_dir, error=e),
                    )
                    if not choose_other:
                        self._status.configure(
                            text=tr("gui.out_canceled"),
                            text_color="#ff5555",
                        )
                        return None
                    chosen = self._choose_output_dir(out_dir.parent if out_dir.parent.exists() else None)
                    if chosen is None:
                        self._status.configure(
                            text=tr("gui.out_canceled"),
                            text_color="#ff5555",
                        )
                        return None
                    out_dir = chosen
                    continue

            write_err = self._check_output_writable(out_dir)
            if write_err is not None:
                choose_other = messagebox.askyesno(
                    tr("gui.out_nowrite_title"),
                    tr("gui.out_nowrite_msg", path=out_dir, error=write_err),
                )
                if not choose_other:
                    self._status.configure(
                        text=tr("gui.out_retry_hint"),
                        text_color="#ff5555",
                    )
                    return None
                chosen = self._choose_output_dir(out_dir)
                if chosen is None:
                    self._status.configure(
                        text=tr("gui.out_canceled"),
                        text_color="#ff5555",
                    )
                    return None
                out_dir = chosen
                continue

            self._out.delete(0, "end")
            self._out.insert(0, str(out_dir))
            return str(out_dir)

    def _state(self) -> dict[str, Any]:
        state: dict[str, Any] = {"lang": self._lang_combo.get()}
        state.update(self.sources_tab.get_state())
        state.update(self.settings_tab.get_state())
        state.update(self.dependencies_tab.get_state())
        state.update(self.updates_tab.get_state())
        return state

    def _save_state(self) -> None:
        try:
            st = self._state()
            del st["_has_inputs"]
            st["input_mode"] = (
                "steam" if self._in_mode.get() == tr("gui.mode_steam") else "local"
            )
            st["version"] = 1
            save_gui_state(st)
        except OSError:
            pass

    def _apply_state(self, raw: dict[str, Any]) -> None:
        m = merge_gui_state(raw, self._bd, self._repo_root)
        defaults = default_gui_state(self._bd, self._repo_root)
        lg = m["lang"]
        self._lang_combo.set(lg)
        set_lang(lg)
        self._out.delete(0, "end")
        self._out.insert(0, str(m.get("output", "q3")))
        self._listbox.delete(0, END)
        for p in _as_str_list(m.get("paths")):
            self._listbox.insert(END, p)
        self._refresh_local_placeholder()
        self._ws_listbox.delete(0, END)
        for x in _as_str_list(m.get("workshop_list")):
            self._ws_listbox.insert(END, x)
        self._col_listbox.delete(0, END)
        for x in _as_str_list(m.get("collection_list")):
            self._col_listbox.insert(END, x)
        for key, _ in CHK_DEF:
            if m.get(key, False):
                self._chk[key][0].select()
            else:
                self._chk[key][0].deselect()
        for key in ("check_updates_on_start", "auto_download_update"):
            if m.get(key, False):
                self._chk[key][0].select()
            else:
                self._chk[key][0].deselect()
        self._bsp_patch.set(str(_safe_int(m.get("bsp_patch_method"), 1)))
        for nk, defv in [
            ("coworkers", 3),
            ("pool_max", 96),
            ("aas_timeout", 90),
            ("bspc_concurrent", 1),
        ]:
            self._num[nk].delete(0, "end")
            self._num[nk].insert(0, str(_safe_int(m.get(nk), defv)))
        self._aas_threads.delete(0, "end")
        self._aas_threads.insert(0, str(m.get("aas_threads", "")).strip())
        for nk in ("bspc", "levelshot", "steamcmd", "ffmpeg", "ql_pak"):
            val = str(m.get(nk, ""))
            if "_MEI" in val and not Path(val).exists():
                val = str(defaults.get(nk, val))
            self._path[nk].delete(0, "end")
            self._path[nk].insert(0, val)
        self._refresh_all_tool_path_status()
        self._log_path.delete(0, "end")
        self._log_path.insert(0, str(m.get("log", "")).strip())
        self._on_lang(lg)
        self._in_mode.set(
            tr("gui.mode_steam")
            if m.get("input_mode") == "steam"
            else tr("gui.mode_local")
        )
        self._on_in_mode(self._in_mode.get())
        self._latest_known_version = str(m.get("latest_known_version", "")).strip()
        self._refresh_latest_version_label()

    def _load_state(self) -> None:
        try:
            raw = load_gui_state()
            if isinstance(raw, dict):
                self._apply_state(raw)
        except Exception:
            pass

    def _reset_gui_defaults(self) -> None:
        self._apply_state(default_gui_state(self._bd, self._repo_root))

    def _add_files(self) -> None:
        fs = filedialog.askopenfilenames(filetypes=[("pk3", "*.pk3"), ("All", "*.*")])
        for f in fs:
            self._listbox.insert(END, f)
        self._refresh_local_placeholder()

    def _add_dir(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self._listbox.insert(END, d)
        self._refresh_local_placeholder()

    def _remove_sel(self) -> None:
        for i in reversed(self._listbox.curselection()):
            self._listbox.delete(i)
        self._refresh_local_placeholder()

    def _clear_list(self) -> None:
        self._listbox.delete(0, END)
        self._refresh_local_placeholder()

    def _on_log_scroll(self, _event: Any = None) -> None:
        self.after(50, self._check_log_at_bottom)

    def _check_log_at_bottom(self) -> None:
        try:
            yview = self._log_box.yview()
            self._log_autoscroll = yview[1] >= 0.99
        except Exception:
            pass

    def _clear_log(self) -> None:
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        self._log_autoscroll = True

    def _copy_log(self) -> None:
        text = self._log_box.get("1.0", "end-1c")
        if not text.strip():
            self._status.configure(text=tr("gui.log_empty"), text_color="#aaaaaa")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status.configure(text=tr("gui.log_copied"), text_color="#55ff55")

    def _save_log_to_file(self) -> None:
        text = self._log_box.get("1.0", "end-1c")
        if not text.strip():
            self._status.configure(text=tr("gui.log_empty"), text_color="#aaaaaa")
            return
        target = filedialog.asksaveasfilename(
            title=tr("gui.save_log"),
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
            initialfile="qltoq3-log.txt",
        )
        if not target:
            return
        try:
            Path(target).write_text(text, encoding="utf-8")
        except OSError as e:
            self._status.configure(
                text=tr("gui.log_save_failed", error=e),
                text_color="#ff5555",
            )
            return
        self._status.configure(text=tr("gui.log_saved"), text_color="#55ff55")

    def _append_log_chunk(self, chunk: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", chunk)
        if self._log_autoscroll:
            self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _spinner_stop(self) -> None:
        if self._spinner_after_id is not None:
            try:
                self.after_cancel(self._spinner_after_id)
            except Exception:
                pass
            self._spinner_after_id = None
        self._lbl_spinner.configure(text="")

    def _spinner_tick(self) -> None:
        self._spinner_after_id = None
        if not self._running:
            return
        self._spinner_idx = (self._spinner_idx + 1) % len(_SPINNER_FRAMES)
        self._lbl_spinner.configure(text=_SPINNER_FRAMES[self._spinner_idx])
        self._spinner_after_id = self.after(_SPINNER_MS, self._spinner_tick)

    def _spinner_start(self) -> None:
        self._spinner_stop()
        self._spinner_idx = 0
        self._lbl_spinner.configure(text=_SPINNER_FRAMES[0])
        self._spinner_after_id = self.after(_SPINNER_MS, self._spinner_tick)

    def _elapsed_stop(self) -> None:
        if self._elapsed_after_id is not None:
            try:
                self.after_cancel(self._elapsed_after_id)
            except Exception:
                pass
            self._elapsed_after_id = None
        self._run_started_t = None
        self._lbl_run_elapsed.configure(text="")

    def _elapsed_tick(self) -> None:
        self._elapsed_after_id = None
        if not self._running or self._run_started_t is None:
            return
        elapsed = time.perf_counter() - self._run_started_t
        self._lbl_run_elapsed.configure(
            text=tr("gui.elapsed", t=_format_elapsed_sec(elapsed))
        )
        self._elapsed_after_id = self.after(1000, self._elapsed_tick)

    def _elapsed_start(self) -> None:
        self._elapsed_stop()
        self._run_started_t = time.perf_counter()
        self._lbl_run_elapsed.configure(
            text=tr("gui.elapsed", t=_format_elapsed_sec(0))
        )
        self._elapsed_after_id = self.after(1000, self._elapsed_tick)

    def _set_run_progress(self, cur: int, total: int, name: str = "") -> None:
        if total <= 0:
            return
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress.set(min(1.0, max(0.0, cur / float(total))))
        self._lbl_progress_detail.configure(
            text=tr("gui.progress_packs", cur=cur, total=total, name=name or "...")
        )

    def _set_run_action(self, action: str) -> None:
        self._lbl_progress_action.configure(
            text=tr("gui.progress_action", action=action)
        )

    def _set_run_phase(self, kind: str, n: int) -> None:
        if kind == "deferred":
            self._progress.stop()
            self._progress.configure(mode="indeterminate")
            self._progress.start()
            msg = tr("gui.phase_deferred", n=n)
            self._lbl_progress_detail.configure(text=msg)
            self._status.configure(text=msg, text_color="#aaaaaa")

    def _run(self) -> None:
        if self._running:
            return
        st = self._state()
        if not st["output"]:
            self._status.configure(text=tr("gui.err_output"), text_color="#ff5555")
            return
        prepared_output = self._prepare_output_dir(st["output"])
        if prepared_output is None:
            return
        st["output"] = prepared_output
        if not st["_has_inputs"]:
            self._status.configure(text=tr("gui.err_paths"), text_color="#ff5555")
            return
        self._show_log_tab()
        del st["_has_inputs"]
        argv = build_argv(st)
        cmd = build_cli_cmd(argv)
        self._user_stopped = False
        self._running = True
        self._btn_run.configure(state="disabled")
        self._btn_stop.configure(state="normal")
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress.set(0)
        self._lbl_progress_detail.configure(text=tr("gui.progress_starting"))
        self._lbl_progress_action.configure(text="")
        self._status.configure(text=tr("gui.running"), text_color="#aaaaaa")
        self._append_log_chunk(subprocess.list2cmdline(cmd) + "\n")
        self._worker = WorkerThread(
            cmd=cmd,
            cwd=os.getcwd(),
            on_started=lambda proc: self.after(0, self._on_worker_started, proc),
            on_progress=lambda cur, total, name: self.after(
                0, self._set_run_progress, cur, total, name
            ),
            on_phase=lambda kind, n: self.after(0, self._set_run_phase, kind, n),
            on_action=lambda action: self.after(0, self._set_run_action, action),
            on_log_line=lambda text: self.after(0, self._append_log_chunk, text),
            on_done=lambda rc: self.after(0, self._finish_run, rc),
            on_start_error=lambda err: self.after(0, self._on_worker_start_error, err),
        )
        self._worker.start()

    def _on_worker_started(self, proc: subprocess.Popen[str]) -> None:
        self._proc = proc
        self._spinner_start()
        self._elapsed_start()

    def _on_worker_start_error(self, message: str) -> None:
        self._running = False
        self._worker = None
        self._proc = None
        self._btn_run.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        self._progress.stop()
        self._progress.set(0)
        self._append_log_chunk(message + "\n")
        self._status.configure(text=message, text_color="#ff5555")

    def _finish_run(self, code: int) -> None:
        self._spinner_stop()
        stopped = self._user_stopped
        elapsed_sec: float | None = None
        if stopped:
            if self._stop_elapsed_snapshot is not None:
                elapsed_sec = self._stop_elapsed_snapshot
                self._stop_elapsed_snapshot = None
            elif self._run_started_t is not None:
                elapsed_sec = time.perf_counter() - self._run_started_t
        elif self._run_started_t is not None:
            elapsed_sec = time.perf_counter() - self._run_started_t
        self._elapsed_stop()
        self._running = False
        self._worker = None
        self._proc = None
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress.set(0)
        self._lbl_progress_detail.configure(text="")
        self._lbl_progress_action.configure(text="")
        self._btn_run.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        self._user_stopped = False
        td = _format_elapsed_sec(elapsed_sec) if elapsed_sec is not None else "—"
        if stopped:
            self._status.configure(
                text=tr("gui.stopped_elapsed", t=td), text_color="#ffff55"
            )
        elif code == 0:
            self._status.configure(
                text=tr("gui.done_ok", code=code, t=td), text_color="#55ff55"
            )
        else:
            self._status.configure(
                text=tr("gui.done_err", code=code, t=td), text_color="#ff5555"
            )
    def _stop(self) -> None:
        if self._running and self._worker is not None:
            self._user_stopped = True
            self._worker.terminate()
            if self._run_started_t is not None:
                et = time.perf_counter() - self._run_started_t
                msg = tr("gui.stopped_elapsed", t=_format_elapsed_sec(et))
            else:
                msg = tr("gui.stopped")
            self._append_log_chunk("\n" + msg + "\n")
            self._status.configure(text=msg, text_color="#ffff55")

    def _open_credit(self) -> None:
        webbrowser.open("https://q3unite.su/")

    def _on_close(self) -> None:
        pending_installer = self._pending_update_installer
        pending_latest = self._pending_update_version
        self._pending_update_installer = None
        self._pending_update_version = ""
        self._spinner_stop()
        if self._running and self._worker is not None:
            if self._run_started_t is not None:
                self._stop_elapsed_snapshot = time.perf_counter() - self._run_started_t
            self._user_stopped = True
            self._worker.terminate()
        self._elapsed_stop()
        self._refresh_update_install_button()
        tp = getattr(self, "_temp_ico_path", None)
        if tp is not None:
            try:
                Path(tp).unlink(missing_ok=True)
            except OSError:
                pass
        self._save_state()
        self.destroy()
        if pending_installer and pending_latest and pending_installer.is_file():
            try:
                subprocess.Popen(
                    [
                        str(pending_installer),
                        "/VERYSILENT",
                        "/SUPPRESSMSGBOXES",
                        "/NORESTART",
                        "/SP-",
                    ],
                    cwd=str(pending_installer.parent),
                )
            except OSError as e:
                print(tr("gui.update_run_failed", error=e), file=sys.stderr)


def _patch_tkinter_py314() -> None:
    if sys.version_info < (3, 14):
        return
    import tkinter as tk

    def nametowidget(self: Any, name: Any) -> Any:
        parts = str(name).split(".")
        w = self
        if not parts[0]:
            w = tk.Misc._root(w)
            parts = parts[1:]
        for n in parts:
            if not n:
                break
            w = w.children[n]
        return w

    tk.Misc.nametowidget = nametowidget
    tk.Misc._nametowidget = nametowidget

    def _report_exception(self: Any) -> None:
        exc, val, tb = sys.exc_info()
        root = tk.Misc._root(self)
        root.report_callback_exception(exc, val, tb)

    tk.Misc._report_exception = _report_exception


def main() -> None:
    _patch_tkinter_py314()
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "QLtoQ3.QLtoQ3.GUI.1"
            )
        except Exception:
            pass
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    if sys.platform == "win32":
        ctk.CTk._deactivate_windows_window_header_manipulation = True
    app = QlToQ3App()
    app.mainloop()


if __name__ == "__main__":
    main()
