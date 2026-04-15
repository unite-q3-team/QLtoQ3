"""argparse for qltoq3."""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile

from .constants import bundled_dir, repo_root
from .l10n import default_lang_from_env, tr


def _workshop_pack_paths(wdir: str) -> list[str]:
    out: list[str] = []
    if not os.path.isdir(wdir):
        return out
    for name in os.listdir(wdir):
        fp = os.path.join(wdir, name)
        if not os.path.isfile(fp):
            continue
        low = name.lower()
        if low.endswith(".pk3"):
            out.append(fp)
        elif low.endswith(".bin"):
            try:
                if zipfile.is_zipfile(fp):
                    out.append(fp)
            except OSError:
                pass
    return out


def mk_parser():
    bd = bundled_dir()
    _root = repo_root()
    p = argparse.ArgumentParser(description=tr("help.desc"))
    p.add_argument("paths", nargs="*", help=tr("help.paths"))
    p.add_argument("--output", "-o", default="q3", help=tr("help.output"))
    p.add_argument("--yes-always", action="store_true", help=tr("help.yes_always"))
    p.add_argument("--no-aas", action="store_true", help=tr("help.no_aas"))
    p.add_argument(
        "--lang",
        choices=["en", "ru"],
        default=default_lang_from_env(),
        help=tr("help.lang"),
    )
    p.add_argument(
        "--aas-timeout",
        type=int,
        default=90,
        metavar="SEC",
        help=tr("help.aas_timeout"),
    )
    p.add_argument(
        "--aas-threads",
        type=int,
        default=None,
        metavar="N",
        help=tr("help.aas_threads"),
    )
    p.add_argument(
        "--no-aas-optimize",
        action="store_true",
        help=tr("help.no_aas_optimize"),
    )
    p.add_argument(
        "--aas-geometry-fast",
        action="store_true",
        help=tr("help.aas_geometry_fast"),
    )
    p.add_argument(
        "--aas-bspc-nocsg",
        action="store_true",
        help=tr("help.aas_bspc_nocsg"),
    )
    p.add_argument(
        "--aas-bspc-freetree",
        action="store_true",
        help=tr("help.aas_bspc_freetree"),
    )
    p.add_argument(
        "--aas-bspc-breadthfirst",
        action="store_true",
        help=tr("help.aas_bspc_breadthfirst"),
    )
    p.add_argument(
        "--bspc-concurrent",
        type=int,
        default=1,
        metavar="N",
        help=tr("help.bspc_concurrent"),
    )
    p.add_argument("--force", action="store_true", help=tr("help.force"))
    p.add_argument(
        "--coworkers",
        type=int,
        default=3,
        metavar="N",
        help=tr("help.coworkers"),
    )
    p.add_argument(
        "--pool-max",
        type=int,
        default=96,
        metavar="N",
        help=tr("help.pool_max"),
    )
    p.add_argument("--workshop", nargs="+", help=tr("help.workshop"))
    p.add_argument(
        "--collection",
        nargs="+",
        help=tr("help.collection"),
    )
    p.add_argument("--optimize", action="store_true", help=tr("help.optimize"))
    p.add_argument(
        "--bsp-patch-method",
        type=int,
        choices=[1, 2],
        default=1,
        help=tr("help.bsp_patch_method"),
    )
    p.add_argument("--bspc", default=os.path.join(bd, "bspc.exe"), help=tr("help.bspc"))
    p.add_argument(
        "--levelshot",
        default=os.path.join(bd, "levelshot.png"),
        help=tr("help.levelshot"),
    )
    p.add_argument(
        "--steamcmd", default=r"C:\steamcmd\steamcmd.exe", help=tr("help.steamcmd")
    )
    p.add_argument("--ffmpeg", default="ffmpeg", help=tr("help.ffmpeg"))
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=tr("help.verbose"),
    )
    p.add_argument(
        "--show-skipped",
        action="store_true",
        help=tr("help.show_skipped"),
    )
    p.add_argument(
        "--hide-converted",
        action="store_true",
        help=tr("help.hide_converted"),
    )
    p.add_argument(
        "--skip-mapless",
        action="store_true",
        help=tr("help.skip_mapless"),
    )
    p.add_argument(
        "--time-stages",
        action="store_true",
        help=tr("help.time_stages"),
    )
    p.add_argument(
        "--dry-run",
        "--list",
        action="store_true",
        dest="dry_run",
        help=tr("help.dry_run"),
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        help=tr("help.no_color"),
    )
    p.add_argument(
        "--no-progress",
        action="store_true",
        help=tr("help.no_progress"),
    )
    p.add_argument(
        "--log",
        metavar="PATH",
        help=tr("help.log"),
    )
    p.add_argument(
        "--ql-pak",
        metavar="PATH",
        dest="ql_pak",
        default=os.path.join(_root, "ql_baseq3", "pak00.pk3"),
        help=tr("help.ql_pak"),
    )
    return p


# ql steam appid
_QL_STEAM_APP_ID = "282440"


def extract_steam_id(token: str) -> str | None:
    s = (token or "").strip()
    if not s:
        return None
    if s.isdigit():
        return s
    candidate = s
    if "://" not in candidate:
        candidate = "https://steamcommunity.com/" + candidate.lstrip("/")
    try:
        parsed = urllib.parse.urlparse(candidate)
        q = urllib.parse.parse_qs(parsed.query)
        vals = q.get("id", [])
        if vals:
            v = vals[0].strip()
            if v.isdigit():
                return v
    except Exception:
        pass
    m = re.search(r"(?:\?|&)id=(\d+)", s)
    if m:
        return m.group(1)
    return None


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    args = mk_parser().parse_args(argv)
    if getattr(args, "aas_geometry_fast", False):
        args.aas_bspc_nocsg = True
        args.aas_bspc_freetree = True
    input_files: list[str] = []
    w_ids: list[str] = []

    if args.collection:
        _col_ids: list[str] = []
        _col_paths: list[str] = []
        for x in args.collection:
            sid = extract_steam_id(x)
            if sid is not None:
                _col_ids.append(sid)
            else:
                _col_paths.append(x)
        args.collection = _col_ids
        if _col_paths:
            args.paths = list(args.paths) + _col_paths

    if args.workshop:
        for x in args.workshop:
            sid = extract_steam_id(x)
            if sid is not None:
                w_ids.append(sid)

    if args.collection:
        for cid in args.collection:
            if not cid.isdigit():
                continue
            req = urllib.request.Request(
                f"https://steamcommunity.com/sharedfiles/filedetails/?id={cid}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    html = resp.read().decode("utf-8")
                    c_ids = list(dict.fromkeys(re.findall(r"sharedfile_(\d+)", html)))
                    c_ids = [x for x in c_ids if x != cid and x != _QL_STEAM_APP_ID]
                    if c_ids:
                        print(f"found {len(c_ids)} item(s) in collection {cid}")
                        w_ids.extend(c_ids)
                    else:
                        print(
                            f"warning: no workshop items parsed for collection {cid} "
                            f"(page layout may have changed; try --workshop <file id>)",
                            file=sys.stderr,
                        )
            except Exception as e:
                print(f"warning: steam collection {cid} failed: {e}", file=sys.stderr)

    w_ids = [x for x in dict.fromkeys(w_ids) if x.isdigit() and x != _QL_STEAM_APP_ID]

    def add_path(p: str):
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in files:
                    if f.lower().endswith(".pk3"):
                        input_files.append(os.path.join(root, f))
        elif os.path.isfile(p) and p.lower().endswith(".pk3"):
            input_files.append(p)

    for p in args.paths:
        add_path(p)

    if w_ids:
        to_download = []
        workshop_base = os.path.join(
            os.path.dirname(args.steamcmd), "steamapps", "workshop", "content", "282440"
        )
        for wid in w_ids:
            found = False
            wdir = os.path.join(workshop_base, wid)
            if os.path.isdir(wdir):
                for fp in _workshop_pack_paths(wdir):
                    input_files.append(fp)
                    found = True
            if not found:
                to_download.append(wid)

        if to_download:
            if not os.path.exists(args.steamcmd):
                print(
                    f"error: steamcmd not found at {args.steamcmd}, cannot download {len(to_download)} item(s)",
                    file=sys.stderr,
                )
            else:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False
                ) as tf:
                    tf.write("login anonymous\n")
                    for wid in to_download:
                        tf.write(f"workshop_download_item 282440 {wid}\n")
                    tf.write("quit\n")
                    script_path = tf.name

                print(f"downloading {len(to_download)} workshop item(s)...")
                subprocess.run([args.steamcmd, "+runscript", script_path])
                try:
                    os.remove(script_path)
                except OSError:
                    pass

                for wid in to_download:
                    wdir = os.path.join(workshop_base, wid)
                    if os.path.isdir(wdir):
                        for fp in _workshop_pack_paths(wdir):
                            input_files.append(fp)

    input_files = sorted(list(set(input_files)))
    return args, input_files
