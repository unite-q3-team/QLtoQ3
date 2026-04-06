"""single pk3 extract -> patch -> repack."""

import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from collections import deque
from typing import Any, Optional

from PIL import Image
from tqdm import tqdm

if os.name == "nt":
    os.system("")

from .constants import BRANDING_COMMENT, BRANDING_TEXT, bundled_dir
from .colors import Colors
from .progress import (
    PHASE_MAP_W,
    WORKER_BAR_FMT,
    get_thread_pos,
    set_worker_state,
    slot_idle,
)
from .ziputil import ZIP_OUT_COMPRESSLEVEL, zip_write_retry
from .qlcache import ql_read
from .shaders import shader_deps, process_shader
from .bsp import strip_ogg, process_bsp
from .md3 import md3_tex
from .media import convert_image, ogg2wav
from .compat import q3_compat
from .l10n import tr
from .aas import aas_header_probe, bspc_aas, map_sort_key


def write_branding_txt(temp_dir: str) -> None:
    with open(os.path.join(temp_dir, "q3unite.su.txt"), "w", encoding="utf-8") as f:
        f.write(BRANDING_TEXT)


def scan_map_tree(temp_dir: str, stats: Optional[dict] = None) -> tuple:
    map_assets: set = set()
    bsp_files, shader_files, model_files, image_files, ogg_files = (
        [],
        [],
        [],
        [],
        [],
    )
    for root, _, files in os.walk(temp_dir):
        for f in files:
            fp = os.path.join(root, f)
            rp = os.path.relpath(fp, temp_dir).lower().replace("\\", "/")
            map_assets.add(rp)
            if rp.startswith("textures/"):
                map_assets.add(os.path.splitext(rp)[0])
            ext = os.path.splitext(f)[1].lower()
            if ext == ".bsp":
                bsp_files.append(fp)
            elif ext == ".shader":
                shader_files.append(fp)
            elif ext == ".md3":
                model_files.append(fp)
            elif ext in [".dds", ".png"]:
                image_files.append(fp)
            elif ext == ".ogg":
                ogg_files.append(fp)
            elif ext == ".aas" and stats is not None:
                aas_header_probe(fp, stats, os.path.basename(f))
    return map_assets, bsp_files, shader_files, model_files, image_files, ogg_files


def extend_used_from_shaders_md3(shader_files: list, model_files: list) -> list:
    out: list[str] = []
    for fp in shader_files:
        try:
            with open(fp, encoding="utf-8", errors="ignore") as f:
                t = f.read()
            out.extend(shader_deps(t))
        except OSError:
            pass
    for fp in model_files:
        texs, _ = md3_tex(fp)
        out.extend(texs)
    return out


def _index_as_dict(idx: Any) -> dict | None:
    if idx is None:
        return None
    if isinstance(idx, dict):
        return idx
    data = getattr(idx, "data", None)
    if isinstance(data, dict):
        return data
    return None


def run_restore_bridge(
    temp_dir: str,
    fn: str,
    index: dict,
    ql_pak00_path: Optional[str],
    optimize: bool,
    ffmpeg_bin: str,
    all_used_resources: list,
    map_assets: set,
    issues: list,
    inner=None,
) -> tuple[int, int, int]:
    ql_files, ql_shaders = index["ql"]["files"], index["ql"]["shaders"]
    q3_files, q3_shaders = set(index["q3"]["files"]), set(index["q3"]["shaders"])
    bridge_shaders: dict = {}
    bridge_files: dict = {}
    to_resolve = deque(set(all_used_resources))
    resolved: set = set()
    last_update = 0.0
    restored = 0
    extra_images = 0
    extra_sounds = 0

    while to_resolve:
        rp = to_resolve.popleft().lower().replace("\\", "/")
        if not rp or rp in resolved:
            continue
        resolved.add(rp)
        if time.time() - last_update > 0.1:
            if inner:
                with tqdm.get_lock():
                    inner.set_postfix_str(
                        f"{tr('pk3.res_prefix')}{os.path.basename(rp)[:15]}"
                    )
            last_update = time.time()
        rb = rp
        for ext in [".tga", ".jpg", ".png", ".dds", ".wav", ".ogg", ".md3"]:
            if rp.endswith(ext):
                rb = rp[: -len(ext)]
                break
        if rp in map_assets or rp in q3_shaders or rb in q3_shaders:
            continue
        found_locally = False
        for ext in ["", ".tga", ".jpg", ".png", ".dds", ".wav", ".ogg", ".md3"]:
            if (rb + ext) in map_assets or (rb + ext) in q3_files:
                found_locally = True
                break
        if found_locally:
            continue
        ql_sn = rp if rp in ql_shaders else (rb if rb in ql_shaders else None)
        if ql_sn and ql_sn not in bridge_shaders:
            bridge_shaders[ql_sn] = ql_shaders[ql_sn][2]
            restored += 1
            for d in shader_deps(bridge_shaders[ql_sn]):
                if d not in resolved:
                    to_resolve.append(d)
        for ext in ["", ".tga", ".jpg", ".png", ".dds", ".wav", ".ogg", ".md3"]:
            t = rb + ext
            if t in ql_files and t not in bridge_files:
                data = ql_read(t, ql_files, issues, ql_pak00_path)
                if data:
                    bridge_files[t] = data
                    restored += 1
                    if t.endswith(".md3"):
                        tf_path = None
                        try:
                            tf = tempfile.NamedTemporaryFile(delete=False)
                            tf_path = tf.name
                            tf.write(data)
                            tf.close()
                            m_texs, m_iss = md3_tex(tf_path)
                            to_resolve.extend(m_texs)
                            issues.extend(m_iss)
                        finally:
                            if tf_path and os.path.isfile(tf_path):
                                try:
                                    os.remove(tf_path)
                                except OSError:
                                    pass
                break

    if bridge_shaders:
        sd = os.path.join(temp_dir, "scripts")
        os.makedirs(sd, exist_ok=True)
        with open(
            os.path.join(sd, f"zzz_{os.path.splitext(fn)[0]}.shader"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(BRANDING_COMMENT)
            for sc in bridge_shaders.values():
                sc2 = (
                    sc.replace(".dds", ".tga")
                    .replace(".png", ".tga")
                    .replace(".DDS", ".tga")
                    .replace(".PNG", ".tga")
                )
                f.write(strip_ogg(sc2) + "\n\n")
    for rp, data in bridge_files.items():
        op = os.path.join(temp_dir, rp)
        os.makedirs(os.path.dirname(op), exist_ok=True)
        with open(op, "wb") as f:
            f.write(data)
        ext_lo = os.path.splitext(rp)[1].lower()
        if ext_lo in [".dds", ".png"]:
            success, err = convert_image(op, optimize)
            if success:
                extra_images += 1
            else:
                issues.append(err)
        elif ext_lo == ".ogg":
            success, err = ogg2wav(op, ffmpeg_bin)
            if success:
                extra_sounds += 1
            else:
                issues.append(err)

    return restored, extra_images, extra_sounds


def convert_pk3(
    in_pk3,
    out_pk3,
    yes_always=False,
    index=None,
    optimize=False,
    bspc_path=None,
    levelshot_src=None,
    skip_aas=False,
    aas_timeout=90,
    aas_threads=None,
    aas_bspc_optimize=True,
    aas_bspc_extra=None,
    force=False,
    main_pbar=None,
    bsp_method=1,
    ffmpeg_bin="ffmpeg",
    slot_pbars=None,
    verbose=False,
    ql_pak00_path=None,
    show_skipped=False,
    hide_converted=False,
    skip_nomap=False,
    bspc_sem=None,
    bspc_wait=None,
    defer_aas=False,
    time_stages=False,
):
    if bspc_path is None:
        bspc_path = os.path.join(bundled_dir(), "bspc.exe")
    if levelshot_src is None:
        levelshot_src = os.path.join(bundled_dir(), "levelshot.png")
    stats = {
        "maps": 0,
        "images": 0,
        "sounds": 0,
        "restored": 0,
        "issues": [],
        "skipped_exists": 0,
        "skipped_compatible": 0,
        "skipped_mapless": 0,
    }
    fn = os.path.basename(in_pk3)
    position = get_thread_pos()

    final_out_pk3 = (
        os.path.join(out_pk3, fn)
        if (os.path.isdir(out_pk3) or out_pk3.endswith(("/", "\\")))
        else out_pk3
    )
    if os.path.exists(final_out_pk3) and not force:
        if show_skipped:
            main_pbar.write(
                f"  {Colors.YELLOW}{tr('pk3.skip_exists', fn=fn)}{Colors.ENDC}"
            )
        stats["skipped_exists"] = 1
        return stats
    if not yes_always and not force and q3_compat(in_pk3):
        if show_skipped:
            main_pbar.write(
                f"  {Colors.YELLOW}{tr('pk3.skip_compat', fn=fn)}{Colors.ENDC}"
            )
        stats["skipped_compatible"] = 1
        return stats

    if skip_nomap:
        try:
            with zipfile.ZipFile(in_pk3, "r") as zf:
                if not any(n.lower().endswith(".bsp") for n in zf.namelist()):
                    if show_skipped:
                        main_pbar.write(
                            f"  {Colors.YELLOW}{tr('pk3.skip_mapless', fn=fn)}{Colors.ENDC}"
                        )
                    stats["skipped_mapless"] = 1
                    return stats
        except (OSError, zipfile.BadZipFile, RuntimeError):
            pass

    start_t = time.time()
    temp_dir = tempfile.mkdtemp(prefix="qltoq3_")
    inner = slot_pbars[position] if slot_pbars else None
    keep_temp = False
    phase_ms = {}
    tc = time.perf_counter()
    try:
        if inner:
            inner.reset(total=8)
            inner.bar_format = WORKER_BAR_FMT
            inner.set_description_str(f"  {Colors.CYAN}{fn[:15]:<15}{Colors.ENDC}")
            inner.n = 0
            inner.refresh()
        if slot_pbars:
            set_worker_state(slot_pbars, position, "run")
        if inner:
            inner.set_postfix_str(tr("pk3.extract"))
        write_branding_txt(temp_dir)
        with zipfile.ZipFile(in_pk3, "r") as zf:
            zf.extractall(temp_dir)
        if time_stages:
            phase_ms["extract"] = (time.perf_counter() - tc) * 1000
        tc = time.perf_counter()
        if inner:
            inner.update(1)

        if inner:
            inner.set_postfix_str(tr("pk3.patch_bsps"))
        (
            map_assets,
            bsp_files,
            shader_files,
            model_files,
            image_files,
            ogg_files,
        ) = scan_map_tree(temp_dir, stats)

        all_used_resources = []
        map_infos = []
        for fp in bsp_files:
            if inner:
                inner.set_postfix_str(f"BSP:{os.path.basename(fp)[:15]}")
            texs, longname, ent_deps, bsp_issues = process_bsp(fp, bsp_method)
            all_used_resources.extend(texs)
            all_used_resources.extend(ent_deps)
            stats["maps"] += 1
            stats["issues"].extend(bsp_issues)
            map_name = os.path.splitext(os.path.basename(fp))[0]
            need_aas = not skip_aas and os.path.exists(bspc_path)
            map_infos.append((fp, map_name, longname, need_aas))
        map_infos.sort(key=map_sort_key)
        defer_aas_pack = (
            defer_aas
            and not skip_aas
            and os.path.exists(bspc_path)
            and any(t[3] for t in map_infos)
        )
        if time_stages:
            phase_ms["bsp"] = (time.perf_counter() - tc) * 1000
        tc = time.perf_counter()
        if inner:
            inner.update(1)

        if inner:
            inner.set_postfix_str(tr("pk3.shaders"))
        for fp in shader_files:
            if inner:
                inner.set_postfix_str(f"SH:{os.path.basename(fp)[:15]}")
            success, err, sh_text = process_shader(fp)
            if not success:
                stats["issues"].append(err)
            elif sh_text is not None:
                all_used_resources.extend(shader_deps(sh_text))
        if time_stages:
            phase_ms["shader"] = (time.perf_counter() - tc) * 1000
        tc = time.perf_counter()
        if inner:
            inner.update(1)

        if inner:
            inner.set_postfix_str(tr("pk3.models"))
        for fp in model_files:
            if inner:
                inner.set_postfix_str(f"MD3:{os.path.basename(fp)[:15]}")
            md3_texs, md3_issues = md3_tex(fp)
            all_used_resources.extend(md3_texs)
            stats["issues"].extend(md3_issues)
        if time_stages:
            phase_ms["md3"] = (time.perf_counter() - tc) * 1000
        tc = time.perf_counter()
        if inner:
            inner.update(1)

        if inner:
            inner.set_postfix_str(tr("pk3.images"))
        for fp in image_files:
            if inner:
                inner.set_postfix_str(f"IMG:{os.path.basename(fp)[:15]}")
            success, err = convert_image(fp, optimize)
            if success:
                stats["images"] += 1
            else:
                stats["issues"].append(err)
        for fp in ogg_files:
            if inner:
                inner.set_postfix_str(f"OGG:{os.path.basename(fp)[:15]}")
            success, err = ogg2wav(fp, ffmpeg_bin)
            if success:
                stats["sounds"] += 1
            else:
                stats["issues"].append(err)
        if time_stages:
            phase_ms["media"] = (time.perf_counter() - tc) * 1000
        tc = time.perf_counter()
        if inner:
            inner.update(1)

        if inner:
            inner.set_postfix_str(tr("pk3.restore"))

        r, ei, es = 0, 0, 0
        if index is not None:
            r, ei, es = run_restore_bridge(
                temp_dir,
                fn,
                index,
                ql_pak00_path,
                optimize,
                ffmpeg_bin,
                all_used_resources,
                map_assets,
                stats["issues"],
                inner,
            )
        stats["restored"] += r
        stats["images"] += ei
        stats["sounds"] += es
        if time_stages:
            phase_ms["restore"] = (time.perf_counter() - tc) * 1000
        tc = time.perf_counter()
        if inner:
            inner.update(1)

        for fp, map_name, longname, need_aas in map_infos:
            if need_aas and not defer_aas_pack:
                thr = aas_threads if aas_threads is not None else (os.cpu_count() or 4)
                thr = max(1, min(int(thr), 64))
                if inner:
                    inner.set_postfix_str(f"AAS(bspc):{map_name[:PHASE_MAP_W]}")
                _bx = list(aas_bspc_extra or [])
                if verbose and main_pbar:
                    o = " -optimize" if aas_bspc_optimize else ""
                    ex = (" " + " ".join(_bx)) if _bx else ""
                    main_pbar.write(
                        f"  [verbose] bspc -threads {thr}{ex}{o} -bsp2aas {fp}"
                    )
                try:
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
                        slot_pbars,
                        position,
                        bspc_optimize=aas_bspc_optimize,
                        bspc_extra=_bx,
                    )
                except subprocess.TimeoutExpired:
                    stats["issues"].append(
                        f"AAS timeout for {map_name} (huge BSP can need many minutes; try --aas-timeout 600 --aas-threads {thr} or --no-aas)"
                    )
                finally:
                    if slot_pbars:
                        set_worker_state(slot_pbars, position, "run")
            ad = os.path.join(temp_dir, "scripts")
            os.makedirs(ad, exist_ok=True)
            with open(os.path.join(ad, f"{map_name}.arena"), "w") as af:
                af.write(
                    f'{{\n  map "{map_name}"\n  longname "{longname}"\n  type "quake3"\n}}\n'
                )
            lsd = os.path.join(temp_dir, "levelshots")
            os.makedirs(lsd, exist_ok=True)
            if (
                not any(f.startswith(map_name) for f in os.listdir(lsd))
                and levelshot_src
                and os.path.exists(levelshot_src)
            ):
                try:
                    with Image.open(levelshot_src) as img:
                        img.convert("RGB").save(
                            os.path.join(lsd, f"{map_name}.jpg"), "JPEG", quality=90
                        )
                except Exception as e:
                    stats["issues"].append(f"Levelshot error for {map_name}: {str(e)}")
        if time_stages:
            phase_ms["maps_aas"] = (time.perf_counter() - tc) * 1000
        tc = time.perf_counter()
        if inner:
            inner.update(1)

        if defer_aas_pack:
            keep_temp = True
            stats["deferred_aas"] = {
                "temp_dir": temp_dir,
                "final_out_pk3": final_out_pk3,
                "fn": fn,
                "aas_jobs": [(fp, mn, ln) for fp, mn, ln, na in map_infos if na],
                "start_t": start_t,
                "hide_converted": hide_converted,
                "bspc_path": bspc_path,
                "aas_timeout": aas_timeout,
                "aas_threads": aas_threads,
                "aas_bspc_optimize": aas_bspc_optimize,
                "aas_bspc_extra": list(aas_bspc_extra or []),
                "verbose": verbose,
            }
            if time_stages:
                phase_ms["repack"] = 0.0
        else:
            if inner:
                inner.set_description_str(f"  {Colors.CYAN}{fn[:15]:<15}{Colors.ENDC}")
                inner.set_postfix_str(tr("pk3.repack"))
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
            if time_stages:
                phase_ms["repack"] = (time.perf_counter() - tc) * 1000
            if inner:
                inner.update(1)

            if not hide_converted and main_pbar:
                main_pbar.write(
                    f"  {Colors.GREEN}{tr('pk3.ok', fn=fn, sec=f'{time.time()-start_t:.1f}')}{Colors.ENDC}"
                )
        if time_stages:
            stats["phase_ms"] = phase_ms
        return stats
    finally:
        if not keep_temp:
            try:
                shutil.rmtree(temp_dir)
            except OSError as e:
                stats["issues"].append(f"temp dir cleanup: {e}")
        if inner:
            slot_idle(inner, position, slot_pbars)


def extract_pk3(path: str) -> str:
    temp_dir = tempfile.mkdtemp(prefix="qltoq3_")
    write_branding_txt(temp_dir)
    with zipfile.ZipFile(path, "r") as zf:
        zf.extractall(temp_dir)
    return temp_dir


def repack_pk3(temp_dir: str, out_path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with zipfile.ZipFile(
        out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=ZIP_OUT_COMPRESSLEVEL
    ) as zf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                ap = os.path.join(root, file)
                zip_write_retry(zf, ap, os.path.relpath(ap, temp_dir))


class PK3Index:
    __slots__ = ("path", "by_lower")

    def __init__(self, path: str):
        self.path = path
        with zipfile.ZipFile(path, "r") as zf:
            self.by_lower = {n.lower().replace("\\", "/"): n for n in zf.namelist()}


def restore_missing_assets(
    temp_dir: str,
    ql_pak00_path: Optional[str],
    idx: Any,
    fn: str,
    all_used_resources: list,
    map_assets: set,
    optimize: bool,
    ffmpeg_bin: str,
    issues: Optional[list] = None,
) -> tuple[int, int, int]:
    index = _index_as_dict(idx)
    if index is None:
        return 0, 0, 0
    iss = issues if issues is not None else []
    return run_restore_bridge(
        temp_dir,
        fn,
        index,
        ql_pak00_path,
        optimize,
        ffmpeg_bin,
        all_used_resources,
        map_assets,
        iss,
        inner=None,
    )
