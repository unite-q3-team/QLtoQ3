"""bspc bsp2aas + global deferred queue."""

import itertools
import os
import queue
import shutil
import struct
import subprocess
import threading
import time
import zipfile
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from tqdm import tqdm

from . import bsp
from .colors import Colors
from .l10n import tr
from .progress import PHASE_MAP_W, WORKER_BAR_FMT, set_worker_state, slot_idle
from .ziputil import ZIP_OUT_COMPRESSLEVEL, file_busy, zip_write_retry


def bspc_aas_geometry_args(ns: Any) -> list[str]:
    out: list[str] = []
    if getattr(ns, "aas_bspc_nocsg", False):
        out.append("-nocsg")
    if getattr(ns, "aas_bspc_freetree", False):
        out.append("-freetree")
    if getattr(ns, "aas_bspc_breadthfirst", False):
        out.append("-breadthfirst")
    return out


def aas_header_probe(fp, stats, basename):
    for attempt in range(12):
        try:
            with open(fp, "rb") as af:
                h = af.read(8)
            if len(h) < 8 or h[0:4] != b"EAAS" or struct.unpack("<I", h[4:8])[0] != 4:
                for r2 in range(10):
                    try:
                        os.remove(fp)
                        return
                    except OSError as e2:
                        if file_busy(e2) and r2 + 1 < 10:
                            time.sleep(0.04 * (r2 + 1))
                            continue
                        stats["issues"].append(f"AAS remove {basename}: {e2}")
                        return
            return
        except OSError as e:
            if file_busy(e) and attempt + 1 < 12:
                time.sleep(0.04 * (attempt + 1))
                continue
            stats["issues"].append(f"AAS header {basename}: {e}")
            return


def bspc_aas(
    bspc_path,
    thr,
    fp,
    mn,
    aas_timeout,
    verbose,
    inner,
    sem=None,
    bspc_wait=None,
    slot_pbars=None,
    position=0,
    *,
    bspc_optimize=True,
    bspc_extra: list[str] | None = None,
):
    thr = max(1, min(int(thr), 64))
    m = mn[:PHASE_MAP_W] if mn else ""
    geom = bsp.bsp_geometry_hint(fp)
    geom_tag = f" {geom}" if geom else ""
    got = False
    if sem is not None:
        waiting = False
        wait_ui_interval = 0.45
        last_wait_ui = 0.0
        while True:
            if sem.acquire(blocking=False):
                if waiting and bspc_wait:
                    bspc_wait.dec()
                got = True
                break
            if not waiting:
                if bspc_wait:
                    bspc_wait.inc()
                waiting = True
                if slot_pbars:
                    set_worker_state(slot_pbars, position, "wait")
            if inner:
                now = time.monotonic()
                if now - last_wait_ui >= wait_ui_interval:
                    last_wait_ui = now
                    with tqdm.get_lock():
                        inner.set_postfix_str(
                            f"AAS(bspc):{m}{geom_tag} {Colors.ORANGE}{tr('aas.waiting')}{Colors.ENDC}"
                        )
                        inner.refresh()
            time.sleep(0.06)

    if slot_pbars:
        set_worker_state(slot_pbars, position, "bspc")

    cmd = [bspc_path, "-threads", str(thr)]
    if bspc_extra:
        cmd.extend(bspc_extra)
    if bspc_optimize:
        cmd.append("-optimize")
    cmd.extend(["-bsp2aas", fp])
    ev = threading.Event()
    fm = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def spin():
        n = 0
        while not ev.wait(0.12):
            if inner:
                with tqdm.get_lock():
                    inner.set_postfix_str(f"AAS(bspc):{m}{geom_tag} {fm[n % len(fm)]}")
                    inner.refresh()
            n += 1

    th = None
    if inner:
        th = threading.Thread(target=spin, daemon=True)
        th.start()
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE if verbose else subprocess.DEVNULL,
            timeout=aas_timeout,
        )
    finally:
        if os.name == "nt":
            time.sleep(0.06)
        ev.set()
        if th is not None:
            th.join(timeout=0.5)
        if inner:
            with tqdm.get_lock():
                inner.set_postfix_str(f"AAS(bspc):{m}{geom_tag}")
        if got and sem is not None:
            sem.release()


def generate_aas(
    m_path: str,
    bspc_bin: str = "bspc.exe",
    timeout: int = 90,
    threads=None,
    *,
    bspc_optimize=True,
    bspc_extra: list[str] | None = None,
) -> None:
    thr = max(1, int(threads if threads is not None else (os.cpu_count() or 4)))
    mn = os.path.splitext(os.path.basename(m_path))[0]
    bspc_aas(
        bspc_bin,
        thr,
        m_path,
        mn,
        timeout,
        False,
        None,
        None,
        None,
        None,
        0,
        bspc_optimize=bspc_optimize,
        bspc_extra=bspc_extra,
    )


def pk3_bsp_load_sort_key(pk3_path):
    try:
        with zipfile.ZipFile(pk3_path, "r") as zf:
            maxs, total = 0, 0
            for n in zf.namelist():
                if not n.lower().endswith(".bsp"):
                    continue
                try:
                    s = zf.getinfo(n).file_size
                except KeyError:
                    continue
                maxs = max(maxs, s)
                total += s
    except (OSError, zipfile.BadZipFile, RuntimeError):
        return (1 << 62, 1 << 62, os.path.basename(pk3_path))
    return (maxs, total, os.path.basename(pk3_path))


def map_sort_key(tup):
    fp, map_name, longname, need_aas = tup
    try:
        sz = os.path.getsize(fp)
    except OSError:
        sz = 1 << 62
    if not need_aas:
        return (0, 0, map_name)
    return (1, sz, map_name)


def aas_slot_desc(pk3_basename, map_name):
    stem = os.path.splitext(pk3_basename)[0]
    m = (map_name or "")[:PHASE_MAP_W]
    s = f"{stem}:{m}"
    if len(s) > 22:
        s = s[:19] + "..."
    return f"  {Colors.CYAN}{s:<22}{Colors.ENDC}"


def aas_exec_plan(n, max_w, nw, bspc_sem):
    max_w = max(1, min(max_w, n))
    if bspc_sem is not None:
        exec_workers = min(n, max_w + 4)
    else:
        exec_workers = min(n, max_w)

    pool_sz = 0
    display_pool = None
    if nw > 0 and exec_workers <= nw:
        pool_sz = exec_workers
        display_pool = queue.Queue()
        for p in range(1, pool_sz + 1):
            display_pool.put(p)
    return exec_workers, pool_sz, display_pool


def run_deferred_aas_phase(
    deferred_list,
    bspc_concurrent,
    main_pbar,
    issues,
    *,
    slot_pbars=None,
    bspc_sem=None,
    bspc_wait=None,
):
    if not deferred_list:
        return
    flat = []
    for did, d in enumerate(deferred_list):
        for fp, map_name, longname in d["aas_jobs"]:
            try:
                sz = os.path.getsize(fp)
            except OSError:
                sz = 1 << 62
            flat.append((sz, fp, map_name, longname, did, d))
    flat.sort(key=lambda x: (x[0], x[1], x[2]))
    n = len(flat)
    if n == 0:
        return
    remain = {i: len(d["aas_jobs"]) for i, d in enumerate(deferred_list)}
    lock = threading.Lock()

    max_w = (
        bspc_concurrent
        if bspc_concurrent > 0
        else min(n, max(32, (os.cpu_count() or 4) * 4))
    )
    max_w = max(1, min(max_w, n))

    nw = len(slot_pbars) if slot_pbars else 0
    exec_workers, pool_sz, display_pool = aas_exec_plan(n, max_w, nw, bspc_sem)
    sticky_free_slots = display_pool is None and nw > 0 and slot_pbars
    free_slots = deque(range(1, nw + 1)) if sticky_free_slots else None
    free_slot_lock = threading.Lock() if sticky_free_slots else None

    rid_counter = itertools.count(1)
    aas_running = {}
    aas_running_lock = threading.Lock()

    def touch_postfix():
        if not main_pbar:
            return
        with aas_running_lock:
            parts = [aas_running[k] for k in sorted(aas_running.keys())]
        if not parts:
            suf = ""
        else:
            joined = " | ".join(parts)
            if len(joined) > 140:
                joined = joined[:137] + "..."
            suf = joined
        with tqdm.get_lock():
            main_pbar.set_postfix_str(suf)
            main_pbar.refresh()

    def refresh_slots(full=False):
        if not slot_pbars:
            return
        with tqdm.get_lock():
            if full:
                keys = sorted(slot_pbars.keys(), reverse=True)
            elif pool_sz > 0:
                keys = [
                    p for p in sorted(slot_pbars.keys(), reverse=True) if p <= pool_sz
                ]
            elif sticky_free_slots:
                keys = sorted(slot_pbars.keys(), reverse=True)
            else:
                keys = []
            for p in keys:
                try:
                    slot_pbars[p].refresh()
                except Exception:
                    pass

    def repack_one(d):
        temp_dir = d["temp_dir"]
        final_out_pk3 = d["final_out_pk3"]
        fn = d["fn"]
        start_t = d["start_t"]
        hide_converted = d["hide_converted"]
        os.makedirs(os.path.dirname(os.path.abspath(final_out_pk3)), exist_ok=True)
        with zipfile.ZipFile(
            final_out_pk3,
            "w",
            zipfile.ZIP_DEFLATED,
            compresslevel=ZIP_OUT_COMPRESSLEVEL,
        ) as zf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    ap = os.path.join(root, file)
                    zip_write_retry(
                        zf,
                        ap,
                        os.path.relpath(ap, temp_dir),
                    )
        if not hide_converted and main_pbar:
            main_pbar.write(
                f"  {Colors.GREEN}ok {fn} in {time.time()-start_t:.1f}s{Colors.ENDC}"
            )
        try:
            shutil.rmtree(temp_dir)
        except OSError as e:
            issues.append(f"{fn}: temp dir cleanup: {e}")

    def one(job):
        _sz, fp, map_name, longname, did, d = job
        thr = d.get("aas_threads")
        thr = thr if thr is not None else (os.cpu_count() or 4)
        thr = max(1, min(int(thr), 64))
        bspc_path = d["bspc_path"]
        aas_timeout = d["aas_timeout"]
        verbose = d["verbose"]
        fn = d["fn"]
        pos = None
        inner = None
        if display_pool is not None:
            pos = display_pool.get()
            inner = slot_pbars[pos]
            with tqdm.get_lock():
                inner.bar_format = WORKER_BAR_FMT
                inner.mininterval = 0
                inner.set_description_str(aas_slot_desc(fn, map_name))
                inner.reset(total=1)
                inner.n = 0
                inner.refresh()
        elif sticky_free_slots:
            with free_slot_lock:
                pos = free_slots.popleft() if free_slots else None
            if pos is not None:
                inner = slot_pbars[pos]
                with tqdm.get_lock():
                    inner.bar_format = WORKER_BAR_FMT
                    inner.mininterval = 0
                    inner.set_description_str(aas_slot_desc(fn, map_name))
                    inner.reset(total=1)
                    inner.n = 0
                    inner.refresh()
        rid = next(rid_counter)
        with aas_running_lock:
            aas_running[rid] = (
                f"{os.path.splitext(fn)[0][:12]}:{map_name[:PHASE_MAP_W]}"
            )
        touch_postfix()
        out = (did, fn, None)
        try:
            opt = bool(d.get("aas_bspc_optimize", True))
            extra = list(d.get("aas_bspc_extra") or [])
            if verbose and main_pbar:
                o = " -optimize" if opt else ""
                ex = (" " + " ".join(extra)) if extra else ""
                main_pbar.write(f"  [verbose] bspc -threads {thr}{ex}{o} -bsp2aas {fp}")
            bspc_aas(
                bspc_path,
                thr,
                fp,
                map_name,
                aas_timeout,
                verbose,
                inner,
                bspc_sem,
                bspc_wait,
                slot_pbars if pos is not None else None,
                pos or 0,
                bspc_optimize=opt,
                bspc_extra=extra,
            )
        except subprocess.TimeoutExpired:
            out = (
                did,
                fn,
                f"AAS timeout for {map_name} (huge BSPs can need a lot of time; try --aas-timeout 600 --aas-threads {thr} or --no-aas)",
            )
        except Exception as e:
            out = (did, fn, f"AAS error for {map_name}: {type(e).__name__}: {e}")
        finally:
            with aas_running_lock:
                aas_running.pop(rid, None)
            touch_postfix()
            if display_pool is not None and pos is not None:
                with tqdm.get_lock():
                    slot_idle(inner, pos, slot_pbars)
                display_pool.put(pos)
            elif sticky_free_slots and pos is not None and inner is not None:
                with tqdm.get_lock():
                    slot_idle(inner, pos, slot_pbars)
                with free_slot_lock:
                    free_slots.append(pos)
        return out

    if main_pbar:
        with tqdm.get_lock():
            main_pbar.set_postfix_str("")
            main_pbar.reset(total=n)
            main_pbar.set_description_str(
                f"{Colors.BOLD}{tr('aas.global')}{Colors.ENDC}"
            )
            main_pbar.refresh()
        refresh_slots(full=True)
    with ThreadPoolExecutor(max_workers=exec_workers) as ex:
        futs = [ex.submit(one, job) for job in flat]
        for fut in as_completed(futs):
            did, fn, err = fut.result()
            if err:
                issues.append(f"{fn}: {err}")
            with lock:
                remain[did] -= 1
                if remain[did] == 0:
                    repack_one(deferred_list[did])
            if main_pbar:
                with tqdm.get_lock():
                    main_pbar.update(1)
                refresh_slots(full=False)

    if main_pbar:
        with tqdm.get_lock():
            main_pbar.set_postfix_str("")
            main_pbar.refresh()
        refresh_slots(full=True)
