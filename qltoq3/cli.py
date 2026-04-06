"""cli entry."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import traceback
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from threading import Lock
from typing import Any, Iterable

from tqdm import tqdm

from . import (
    aas,
    bsp,
    colors,
    compat,
    constants,
    l10n,
    media,
    pk3,
    progress,
    qlcache,
    shaders,
    ziputil,
)
from .colors import Colors, apply_gradient
from .compat import q3_compat
from .constants import bundled_dir, repo_root
from .l10n import lang_from_argv, set_lang, tr
from .progress import format_elapsed as _format_elapsed_sec


def _gui_stdout_line(s: str) -> None:
    if not s.endswith("\n"):
        s += "\n"
    with tqdm.get_lock():
        sys.stdout.write(s)
        sys.stdout.flush()


def _report_action(action_key: str) -> None:
    if "--no-progress" in sys.argv:
        _gui_stdout_line(f"QLTOQ3_ACTION {tr(action_key)}")


def pool_workers(
    n_files: int, coworkers: int, bspc_concurrent: int, pool_max: int = 96
) -> int:
    w = max(1, int(coworkers))
    nf = max(0, int(n_files))
    bc = max(0, int(bspc_concurrent))
    pool_cap = max(1, min(512, int(pool_max)))
    if nf == 0:
        return w
    if bc == 0:
        return min(nf, w)
    base = w + (w - bc) if bc < w else w
    extra = min(64, max(8, nf // 4))
    slack = w + extra
    return min(nf, min(pool_cap, max(base, slack)))


def convert_one(
    path: str,
    output_base: str,
    args: Any,
    ql_pak00: pk3.PK3Index | None,
    idx: qlcache.AssetIndex | None,
    stats_lock: Lock,
    stats: dict[str, int],
    slot_pbars: Any | None = None,
    bspc_sem: threading.Semaphore | None = None,
    bspc_wait: progress.BspcWait | None = None,
) -> None:
    fn = os.path.basename(path)
    if os.path.isdir(path):
        out_fn = fn + ".pk3"
    elif fn.lower().endswith(".pk3"):
        out_fn = fn
    elif fn.lower().endswith(".bin"):
        out_fn = os.path.splitext(fn)[0] + ".pk3"
    else:
        out_fn = fn
    out_path = os.path.join(output_base, out_fn)

    _np = args.no_progress
    position = progress.get_thread_pos()
    inner: Any | None = None
    tmpdir: str | None = None

    if not args.force and os.path.exists(out_path):
        msg = tr("pk3.skip_exists", fn=fn)
        if args.show_skipped or _np:
            tqdm.write(msg)
        with stats_lock:
            stats["skipped_exists"] += 1
        return

    if not args.force and not os.path.isdir(path) and q3_compat(path):
        msg = tr("pk3.skip_compat", fn=fn)
        if args.show_skipped or _np:
            tqdm.write(msg)
        with stats_lock:
            stats["skipped_q3"] += 1
        return

    starttime = time.perf_counter()
    tmpdir = pk3.extract_pk3(path)
    try:
        maps: list[str] = []
        for root, _, files in os.walk(tmpdir):
            for f in files:
                if f.lower().endswith(".bsp"):
                    maps.append(os.path.join(root, f))

        if args.skip_mapless and not maps and not args.force:
            msg = tr("pk3.skip_mapless", fn=fn)
            if args.show_skipped or _np:
                tqdm.write(msg)
            with stats_lock:
                stats["skipped_mapless"] += 1
            return

        if slot_pbars and position in slot_pbars:
            inner = slot_pbars[position]
            inner.reset(total=8)
            inner.bar_format = progress.WORKER_BAR_FMT
            inner.set_description_str(f"  {Colors.CYAN}{fn[:15]:<15}{Colors.ENDC}")
            inner.n = 0
            inner.refresh()

        def _phase_start(name: str) -> None:
            if inner:
                inner.set_postfix_str(name)
                with tqdm.get_lock():
                    inner.refresh()

        def _phase_done() -> None:
            if inner:
                inner.update(1)

        (
            map_assets,
            _bsp_paths,
            shader_files,
            model_files,
            _img_paths,
            _ogg_paths,
        ) = pk3.scan_map_tree(tmpdir, None)

        _report_action("pk3.patch_bsps")
        _phase_start("BSP")
        patched_names, bsp_deps = bsp.patch_all_bsps(
            tmpdir, method=args.bsp_patch_method
        )
        _phase_done()

        _report_action("pk3.shaders")
        _phase_start("shaders")
        shaders.fix_all_shaders(tmpdir)
        _phase_done()

        _report_action("pk3.models")
        _phase_start("models")
        media.fix_all_models(tmpdir)
        _phase_done()

        all_used = list(bsp_deps)
        all_used.extend(pk3.extend_used_from_shaders_md3(shader_files, model_files))

        _report_action("pk3.images")
        _phase_start("images")
        img_count = media.convert_all_images(tmpdir, optimize=args.optimize)
        _phase_done()

        _report_action("pk3.sounds")
        _phase_start("sound")
        snd_count = media.convert_all_ogg_to_wav(tmpdir, ffmpeg_bin=args.ffmpeg)
        _phase_done()

        _report_action("pk3.restore")
        _phase_start("restore")
        restored = 0
        extra_img = 0
        extra_snd = 0
        if idx is not None:
            ql_path = ql_pak00.path if ql_pak00 else None
            issues_restore: list[str] = []
            restored, extra_img, extra_snd = pk3.restore_missing_assets(
                tmpdir,
                ql_path,
                idx,
                fn,
                all_used,
                map_assets,
                args.optimize,
                args.ffmpeg,
                issues_restore,
            )
            if issues_restore and args.verbose:
                for line in issues_restore:
                    tqdm.write(line.rstrip("\r\n"))
        img_count += extra_img
        snd_count += extra_snd
        _phase_done()

        _phase_start("AAS")
        if not args.no_aas and maps:
            _report_action("aas.global")
            for m_path in maps:
                mn = os.path.splitext(os.path.basename(m_path))[0]
                thr = (
                    args.aas_threads
                    if args.aas_threads is not None
                    else (os.cpu_count() or 4)
                )
                thr = max(1, min(int(thr), 64))
                aas.bspc_aas(
                    args.bspc,
                    thr,
                    m_path,
                    mn,
                    args.aas_timeout,
                    args.verbose,
                    inner,
                    bspc_sem,
                    bspc_wait,
                    slot_pbars,
                    position,
                    bspc_optimize=not args.no_aas_optimize,
                    bspc_extra=aas.bspc_aas_geometry_args(args),
                )
        _phase_done()

        _report_action("pk3.repack")
        _phase_start("repack")
        pk3.repack_pk3(tmpdir, out_path)
        _phase_done()

        end_t = time.perf_counter()
        if not args.hide_converted:
            tqdm.write(tr("pk3.ok", fn=out_fn, sec=f"{end_t - starttime:.1f}"))

        with stats_lock:
            stats["paks"] += 1
            stats["maps"] += len(patched_names)
            stats["images"] += img_count
            stats["sounds"] += snd_count
            stats["restored"] += restored

    finally:
        if inner is not None:
            progress.slot_idle(inner, position, slot_pbars)
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> None:
    # windows moment
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (AttributeError, Exception):
            pass

    argv = sys.argv[1:]
    lang = lang_from_argv(argv)
    set_lang(lang)

    from .cli_parse import parse_args

    args, input_files = parse_args(argv)

    if args.no_color:
        colors.disable_colors()

    log_file = None
    if args.log:
        try:
            log_file = open(args.log, "a", encoding="utf-8")
        except OSError as e:
            print(f"error: could not open log file: {e}", file=sys.stderr)

    old_stdout = sys.stdout
    old_stderr = sys.stderr

    class Tee:
        def __init__(self, *files: Any):
            self.files = files

        def write(self, obj: str) -> None:
            clean = re.sub(r"\x1b\[[0-9;]*m", "", obj)
            for f in self.files:
                try:
                    f.write(obj if f == old_stdout or f == old_stderr else clean)
                except UnicodeEncodeError:
                    f.write(clean.encode("ascii", "replace").decode("ascii"))

        def flush(self) -> None:
            for f in self.files:
                try:
                    f.flush()
                except Exception:
                    pass

        def __enter__(self) -> "Tee":
            return self

        def __exit__(self, *_: Any) -> None:
            self.flush()

    if log_file:
        sys.stdout = Tee(old_stdout, log_file)  # type: ignore
        sys.stderr = Tee(old_stderr, log_file)  # type: ignore

    try:
        print(apply_gradient(constants.SPLASH))
    except UnicodeEncodeError:
        print("--- qltoq3 ---")

    idx_path = os.path.join(repo_root(), "qltoq3", "bundled", "assets_index.json")
    idx = None
    try:
        idx = qlcache.AssetIndex.load(idx_path)
    except Exception as e:
        if args.verbose:
            print(f"warning: could not load assets index: {e}")

    ql_pak00 = None
    if args.ql_pak and os.path.exists(args.ql_pak):
        try:
            ql_pak00 = pk3.PK3Index(args.ql_pak)
        except Exception as e:
            if args.verbose:
                print(f"warning: could not load ql pak00: {e}")

    if not input_files:
        print(tr("gui.err_paths"))
        return

    if args.dry_run:
        print(tr("dry.title"))
        for f in input_files:
            print(f"  {f}")
        return

    if not os.path.exists(args.output):
        os.makedirs(args.output, exist_ok=True)

    stats = {
        "paks": 0,
        "skipped_exists": 0,
        "skipped_q3": 0,
        "skipped_mapless": 0,
        "failed": 0,
        "maps": 0,
        "images": 0,
        "sounds": 0,
        "restored": 0,
    }
    stats_lock = Lock()

    _np = args.no_progress
    total = len(input_files)
    _bc = max(0, int(getattr(args, "bspc_concurrent", 1)))
    _pm = max(1, min(512, int(getattr(args, "pool_max", 96))))
    _pw = pool_workers(total, args.coworkers, _bc, _pm)
    progress.set_slot_cap(_pw)
    progress.reset_pos_counter()

    tqdm.set_lock(progress.LOG_LOCK)
    slot_pbars = progress.slot_bars(_pw, disable=_np)
    pbar: Any = None
    batch_start_t = time.perf_counter()
    try:
        with tqdm(
            total=total,
            disable=_np,
            desc=f"{Colors.BOLD}{tr('prog.overall')}{Colors.ENDC}",
            bar_format="{l_bar}{bar:28}{r_bar}",
            leave=True,
            position=0,
            file=sys.stdout,
            unit="pk3",
        ) as pbar:
            bspc_sem = threading.Semaphore(_bc) if _bc > 0 else None
            bspc_wait = (
                progress.BspcWait(pbar)
                if _bc > 0 and not args.no_aas and not _np
                else None
            )
            with ThreadPoolExecutor(max_workers=_pw) as executor:
                slots = None if _np else slot_pbars

                def convert_and_report(f: str):
                    convert_one(
                        f,
                        args.output,
                        args,
                        ql_pak00,
                        idx,
                        stats_lock,
                        stats,
                        slots,
                        bspc_sem,
                        bspc_wait,
                    )
                    if _np:
                        with stats_lock:
                            done_count = (
                                stats["paks"]
                                + stats["skipped_exists"]
                                + stats["skipped_q3"]
                                + stats["skipped_mapless"]
                            )
                        _gui_stdout_line(
                            f"QLTOQ3_PROGRESS {done_count}/{total} {os.path.basename(f)}"
                        )

                future_to_path = {
                    executor.submit(convert_and_report, f): f for f in input_files
                }
                for future in as_completed(future_to_path):
                    src = future_to_path[future]
                    try:
                        future.result()
                    except Exception as e:
                        with stats_lock:
                            stats["failed"] += 1
                        tqdm.write(
                            f"{Colors.RED}{os.path.basename(src)}: "
                            f"{type(e).__name__}: {e}{Colors.ENDC}"
                        )
                        if args.verbose:
                            traceback.print_exc()
                    pbar.update(1)
    finally:
        if pbar is not None:
            progress.close_bars(slot_pbars, pbar, _pw)

    print(
        "\n"
        + tr("stats.done", t=_format_elapsed_sec(time.perf_counter() - batch_start_t))
    )
    for k, v in stats.items():
        print(f"{k}: {v}")
    if stats["paks"] == 0:
        if stats.get("failed", 0) > 0:
            print(tr("stats.hint_failures"))
        if stats["skipped_mapless"] > 0:
            print(tr("stats.hint_skip_mapless"))
        if stats["skipped_q3"] > 0:
            print(tr("stats.hint_all_q3_compat"))
        if (
            stats.get("failed", 0) == 0
            and stats["skipped_mapless"] == 0
            and stats["skipped_q3"] == 0
        ):
            print(tr("stats.hint_nothing_written"))

    if log_file:
        try:
            log_file.flush()
        except Exception:
            pass
        finally:
            log_file.close()
    sys.stdout = old_stdout
    sys.stderr = old_stderr


if __name__ == "__main__":
    main()
