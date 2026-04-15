"""ui strings: en + ru. env: QLTOQ3_LANG or LANG (ru* -> ru)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import tomllib  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - py3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

_LANG = "en"

S: dict[str, dict[str, str]] = {
    "en": {},
    "ru": {},
}


def _merge(lang: str, d: dict[str, str]) -> None:
    S[lang].update(d)


_merge(
    "en",
    {
        "help.desc": "ql -> q3 pk3 converter",
        "help.lang": "ui language (en or ru); also qltoq3_lang / lang",
        "help.paths": "input .pk3 files or directories",
        "help.output": "output directory or single .pk3 path",
        "help.yes_always": "convert without compatibility prompt",
        "help.no_aas": "skip bspc / aas generation",
        "help.aas_timeout": "bsp2aas time limit per map in seconds (default: 90; huge maps often need 300-900+)",
        "help.aas_threads": "bspc -threads (default: cpu count; bspc allows at most 64; higher values break threading)",
        "help.no_aas_optimize": "skip bspc -optimize (faster AAS phase; larger .aas - storage dedup only, same bot reachability)",
        "help.aas_geometry_fast": "shorthand for --aas-bspc-nocsg --aas-bspc-freetree (faster, coarser collision prep)",
        "help.aas_bspc_nocsg": "pass bspc -nocsg: skip ChopBrushes CSG (faster; overlapping solids may get worse AAS)",
        "help.aas_bspc_freetree": "pass bspc -freetree: free BSP tree earlier after areas (memory; small speedup on huge maps)",
        "help.aas_bspc_breadthfirst": "pass bspc -breadthfirst: breadth-first BSP build order (speed/quality varies by map)",
        "help.bspc_concurrent": "max simultaneous bspc processes (default: 1; 0 = cap by min(jobs, max(32,cpu*4)), not by --coworkers)",
        "help.force": "overwrite existing outputs; with --skip-mapless, still process pk3 that contain no .bsp",
        "help.coworkers": "parallel pk3 jobs (thread pool may be larger when bspc queues)",
        "help.pool_max": "max thread pool size when bspc limits parallelism (default: 96; max 512)",
        "help.workshop": "steam workshop item id(s)",
        "help.collection": "steam collection page id(s). use -o dir for output; do not put output after --collection. non-numeric tokens: paths or output.",
        "help.optimize": "encode textures as jpeg where safe",
        "help.bsp_patch_method": "entity block patch strategy (1 or 2)",
        "help.bspc": "path to bspc.exe",
        "help.levelshot": "default levelshot image",
        "help.steamcmd": "steamcmd.exe for workshop download",
        "help.ffmpeg": "ffmpeg binary for ogg to wav (q3 uses wav)",
        "help.verbose": "more conversion detail (e.g. bspc stderr); print per-file skip lines",
        "help.show_skipped": "print each skipped pk3; implied by --verbose",
        "help.hide_converted": "hide per-file ok lines",
        "help.skip_mapless": "skip pk3 with no .bsp anywhere in the archive (recursive); use --force to process them anyway",
        "help.time_stages": "aggregate wall time per phase in summary",
        "help.dry_run": "list inputs and planned actions without converting",
        "help.no_color": "disable ansi colors (also no_color env)",
        "help.no_progress": "no tqdm bars; plain lines only (gui uses this and parses qltoq3_progress)",
        "help.log": "append session log to file (ansi stripped)",
        "help.ql_pak": "path to original quake live pak00.pk3 (default: <repo>/ql_baseq3/pak00.pk3)",
        "cfg.col.setting": "setting",
        "cfg.col.value": "value",
        "cfg.title": "run configuration",
        "cfg.output": "output",
        "cfg.pk3_files": "pk3 files",
        "cfg.coworkers": "coworkers",
        "cfg.pool": "pool",
        "cfg.pool_max": "pool-max",
        "cfg.force": "force",
        "cfg.yes_always": "yes-always",
        "cfg.optimize_jpg": "optimize (jpg)",
        "cfg.bsp_patch_method": "bsp-patch-method",
        "cfg.no_aas": "no-aas",
        "cfg.aas_timeout": "aas-timeout",
        "cfg.aas_threads": "aas-threads",
        "cfg.aas_threads_note": "{n} (effective; bspc -threads)",
        "cfg.bspc_concurrent": "bspc-concurrent",
        "cfg.bspc_unlimited": "unlimited",
        "cfg.bspc": "bspc",
        "cfg.levelshot": "levelshot",
        "cfg.ffmpeg": "ffmpeg",
        "cfg.steamcmd": "steamcmd",
        "cfg.verbose": "verbose",
        "cfg.show_skipped": "show-skipped",
        "cfg.hide_converted": "hide-converted",
        "cfg.skip_mapless": "skip-mapless",
        "cfg.dry_list": "dry-run / list",
        "cfg.colors": "colors",
        "cfg.ql_pak00": "ql pak00",
        "cfg.pak00_missing": "not set or file missing",
        "cfg.pak00_sha": "pak00 sha-256",
        "cfg.pak00_no_ref": "no reference hash; integrity not verified",
        "cfg.pak00_no_ref_bundled": "no reference hash (bundled/expected_pak00.sha256)",
        "cfg.pak00_ref_no_ql": "reference set; --ql-pak not given",
        "cfg.pak00_match": "matches reference",
        "cfg.pak00_mismatch": "does not match reference (non-original?)",
        "cfg.log_file": "log file",
        "cfg.workshop": "workshop",
        "cfg.collection": "collection",
        "cfg.yes": "yes",
        "cfg.no": "no",
        "stats.col.metric": "metric",
        "stats.col.value": "value",
        "stats.time": "time elapsed",
        "stats.seconds": "{t:.2f} seconds",
        "stats.paks_done": "paks processed",
        "stats.skipped": "skipped",
        "stats.skipped_detail": "{n} (exists: {ex}, q3-ready: {q3}, no maps: {nm})",
        "stats.maps": "maps patched",
        "stats.images": "images converted",
        "stats.sounds": "sounds (ogg to wav)",
        "stats.restored": "restored assets",
        "stats.phase": "phase {key}",
        "stats.pak00_integrity": "pak00 integrity",
        "stats.pak00_bad": "sha-256 does not match reference (file may not be original ql pak00)",
        "stats.done": "done in {t}",
        "stats.hint_all_q3_compat": "nothing was written while some pk3 were skipped as already q3-like. use --force to convert them anyway.",
        "stats.hint_skip_mapless": "nothing was written: some pk3 were skipped with --skip-mapless (no .bsp found). remove --skip-mapless or add --force to process those packs.",
        "stats.hint_failures": "one or more pk3 failed during conversion (see error lines above). use --verbose for full tracebacks.",
        "stats.hint_nothing_written": "nothing was written (no successful conversions). if you expected output, check errors above or input paths.",
        "dry.title": "dry run - nothing written",
        "dry.out": "out:",
        "dry.q3_compat": "q3-compatible:",
        "dry.exists": "exists:",
        "dry.skip_exists": "skip (output exists)",
        "dry.skip_compat": "skip (already q3-compatible)",
        "dry.would_convert": " -> would convert",
        "lim.title": "tool / input limitations (skipped work)",
        "lim.no_index": "  - assets_index.json: not found at {path}. ql/q3 asset indexing was unavailable; resolution steps were skipped.",
        "lim.no_pak00": "  - pak00.pk3: --ql-pak not set or file missing. quake live-only files were not restored from pak00.",
        "lim.no_bspc": "  - bspc: not found ({path}). aas generation (bsp2aas) was not run.",
        "lim.no_ffmpeg": "  - ffmpeg: not found ({path}). ogg to wav conversion was not performed.",
        "lim.pak00_hash": "  - pak00.pk3: sha-256 does not match the reference hash. the file may not be the official ql pak; assets may be missing or wrong.",
        "warn.title": "warning",
        "warn.no_pak": "  pak00 path not set (--ql-pak) or file missing.",
        "warn.no_pak2": "  ql-only assets won't be copied into the output pk3.",
        "warn.bad_hash": "  pak00.pk3 sha-256 != reference in this repo.",
        "warn.bad_hash2": "  might not be original ql pak; assets can be wrong.",
        "err.index_missing": "assets_index.json not found: {path}",
        "issue.title": "issues",
        "prog.overall": "overall progress",
        "prog.coworker_idle": "< coworker #{n} idle >",
        "prog.bspc_queue": "bspc queue: {n} waiting",
        "aas.global": "aas (global)",
        "aas.waiting": "waiting",
        "interrupt.aas": "interrupted during global aas phase.",
        "interrupt.ctrlc": "interrupted (ctrl+c). queue cancelled; workers finish current pk3.",
        "interrupt.partial": "interrupted - partial totals (not all pk3 are done).",
        "pk3.skip_exists": "skipping (exists): {fn}",
        "pk3.skip_compat": "warning: {fn} is compatible.",
        "pk3.skip_mapless": "skipping (no maps): {fn}",
        "pk3.extract": "extracting",
        "pk3.patch_bsps": "patching bsps",
        "pk3.shaders": "shaders",
        "pk3.models": "models",
        "pk3.images": "images",
        "pk3.restore": "restoring ql",
        "pk3.repack": "repacking",
        "pk3.res_prefix": "res=",
        "pk3.ok": "ok {fn} in {sec}s",
        "chk.root": "assets_index.json root must be a json object",
        "chk.sides": "assets_index.json must contain 'ql' and 'q3'",
        "chk.side_obj": "assets_index.json['{side}'] must be an object",
        "chk.files_shaders": "assets_index.json['{side}'] must contain '{subkey}'",
    },
)

_merge(
    "en",
    {
        "gui.title": "qltoq3",
        "gui.tab_sources": "sources",
        "gui.tab_settings": "settings",
        "gui.tab_dependencies": "dependencies",
        "gui.tab_updates": "updates",
        "gui.tab_logs": "logs",
        "gui.lang_short": "language",
        "gui.out_folder": "output folder (converted pk3 files go here)",
        "gui.browse": "browse",
        "gui.local_drop_hint": "you can drag and drop files or folders here",
        "gui.open_output": "open output",
        "gui.open_output_failed": "cannot open output folder: {error}",
        "gui.pk3_sources": "pk3 files and folders on this machine",
        "gui.add_files": "add files...",
        "gui.add_dir": "add folder...",
        "gui.tip_remove": "remove selected rows from the list",
        "gui.tip_clear": "clear the whole list",
        "gui.tip_add_files": "add one or more .pk3 files",
        "gui.tip_add_dir": "add a folder (scanned for pk3)",
        "gui.tip_browse_out": "choose output folder",
        "gui.log": "output log",
        "gui.log_empty": "log is empty.",
        "gui.log_copied": "log copied.",
        "gui.log_saved": "log saved.",
        "gui.log_save_failed": "cannot save log: {error}",
        "gui.log_hint": "read-only; the exact command line is echoed as the first lines when you run",
        "gui.run": "run",
        "gui.stop": "stop",
        "gui.clear_log": "clear log",
        "gui.copy_log": "copy",
        "gui.save_log": "save to file",
        "gui.running": "running...",
        "gui.done_ok": "finished in {t} (code {code})",
        "gui.done_err": "failed in {t} (code {code})",
        "gui.stopped": "stopped",
        "gui.stopped_elapsed": "stopped - {t}",
        "gui.err_paths": "add at least one input: local pk3/folder, workshop id, or collection id.",
        "gui.err_output": "set an output folder.",
        "gui.header_behavior": "conversion options",
        "gui.header_parallelism": "speed and bot paths",
        "gui.mode_local": "local files",
        "gui.mode_steam": "steam workshop",
        "gui.workshop_ids": "workshop ids",
        "gui.collection_ids": "collection ids",
        "gui.add": "add",
        "gui.opt.yes_always": "don't ask, start converting right away",
        "gui.opt.force": "overwrite files that are already in the output folder",
        "gui.opt.no_aas": "skip bot navigation mesh (faster; bots may not work)",
        "gui.opt.optimize": "shrink textures as jpeg when it is safe",
        "gui.opt.dry_run": "only list what would happen, don't write files",
        "gui.opt.hide_converted": "less chatty log: hide per-file success lines",
        "gui.opt.skip_mapless": "skip pk3 that don't contain a map",
        "gui.opt.verbose": "detailed log: show more of what the tool does",
        "gui.opt.show_skipped": "in the log, print every skipped pack by name",
        "gui.opt.time_stages": "at the end, show how long each stage took",
        "gui.opt.no_aas_optimize": "aas: skip bspc -optimize (faster; larger .aas files)",
        "gui.opt.aas_geometry_fast": "aas: faster/coarser bspc (same as --aas-geometry-fast)",
        "gui.opt.aas_bspc_breadthfirst": "aas: bspc breadth-first bsp order (try if stuck on huge maps)",
        "gui.opt.bsp_patch": "map patch mode (try 2 only if something looks wrong)",
        "gui.num.coworkers": "how many packs to work on at once",
        "gui.num.pool_max": "thread pool cap (leave default unless you know why)",
        "gui.num.aas_timeout": "seconds allowed per map for the bot-path step",
        "gui.num.bspc_concurrent": "how many maps are processed in parallel",
        "gui.num.aas_threads": "cpu threads for one map job (empty = auto)",
        "gui.path.bspc": "map compiler (bspc.exe)",
        "gui.path.levelshot": "default loading screen image",
        "gui.path.steamcmd": "steamcmd (workshop downloads)",
        "gui.path.ffmpeg": "ffmpeg (turns game sounds into wav)",
        "gui.path.ql_pak": "original quake live pak00.pk3",
        "gui.extra_log": "also write the session log to a file",
        "gui.placeholder_auto": "auto",
        "gui.log_path_ph": "optional path for a log file...",
        "gui.credit": "by q3unite.su",
        "gui.reset": "reset settings",
        "gui.section_activity": "activity",
        "gui.elapsed": "elapsed {t}",
        "gui.progress_starting": "starting...",
        "gui.progress_packs": "pack {cur} of {total}: {name}",
        "gui.progress_action": "action: {action}",
        "gui.phase_deferred": "deferred bot-path phase ({n} map(s) queued)...",
        "gui.out_pick_title": "choose output folder",
        "gui.out_not_dir_title": "invalid output path",
        "gui.out_not_dir_msg": "path exists but is not a folder:\n{path}\n\nchoose another output folder.",
        "gui.out_missing_title": "output folder not found",
        "gui.out_missing_msg": "output folder does not exist:\n{path}\n\ncreate it?",
        "gui.out_mkdir_fail_title": "cannot create folder",
        "gui.out_mkdir_fail_msg": "cannot create folder:\n{path}\n\n{error}\n\nchoose another output folder?",
        "gui.out_nowrite_title": "no write access",
        "gui.out_nowrite_msg": "no write access to folder:\n{path}\n\n{error}\n\nchoose another output folder?",
        "gui.out_canceled": "process canceled by user.",
        "gui.out_retry_hint": "choose another output folder and run again.",
        "gui.ws_id_invalid": "enter a valid workshop id or steam link.",
        "gui.col_id_invalid": "enter a valid collection id or steam link.",
        "gui.tmp_found_title": "temporary folders found",
        "gui.tmp_found_msg": "found {n} temporary qltoq3 folder(s) from previous runs.\n\ndelete them now?",
        "gui.tmp_removed": "temporary folders deleted: {n}.",
        "gui.tmp_kept": "temporary folders kept.",
        "gui.tmp_remove_failed": "could not delete {n} temporary folder(s).",
        "gui.opt.check_updates_on_start": "check for updates on startup",
        "gui.opt.auto_download_update": "try to download updates automatically",
        "gui.header_updates": "updates",
        "gui.update_check_now": "check updates now",
        "gui.update_current_label": "current",
        "gui.update_latest_label": "latest",
        "gui.update_checking": "checking for updates...",
        "gui.update_check_failed": "update check failed.",
        "gui.update_none": "you already have the latest version.",
        "gui.update_title": "update available",
        "gui.update_available_msg": "a new version is available.\n\ncurrent: {current}\nlatest: {latest}\n\nopen download page?",
        "gui.update_available_status": "update available: {latest}",
        "gui.update_auto_installed_only": "auto update works only for installed app.",
        "gui.update_download_failed": "cannot download update.",
        "gui.update_integrity_missing": "update integrity file not found.",
        "gui.update_integrity_failed": "update file hash check failed.",
        "gui.update_deferred": "update {latest} is ready. install will start after conversion.",
        "gui.update_silent_start": "installing update {latest}...",
        "gui.update_run_failed": "cannot start installer: {error}",
        "gui.path_status_empty": "path is empty.",
        "gui.path_status_missing": "path not found.",
        "gui.path_status_need_file": "a file is required, not a directory.",
        "gui.path_status_need_dir": "a directory is required, not a file.",
        "gui.path_status_ok": "path found.",
        "tmp.found": "found {n} stale qltoq3 temp folder(s).",
        "tmp.ask_remove": "delete them now? [y/N]: ",
        "tmp.removed": "deleted stale temp folders: {n}.",
        "tmp.kept": "kept stale temp folders.",
        "tmp.noninteractive_skip": "stale temp folders found ({n}); non-interactive mode, keeping them.",
        "tmp.remove_failed": "failed to delete stale temp folder(s): {n}.",
    },
)

_merge(
    "ru",
    {
        "help.desc": "конвертер pk3 ql -> q3",
        "help.lang": "язык интерфейса (en или ru); также qltoq3_lang / lang",
        "help.paths": "входные .pk3 или каталоги",
        "help.output": "каталог вывода или один .pk3",
        "help.yes_always": "ничего не спрашивать",
        "help.no_aas": "не запускать bspc / генерацию aas",
        "help.aas_timeout": "таймаут bsp2aas на карту в секундах (по умолчанию: 90; большие карты часто требуют 300-900+)",
        "help.aas_threads": "bspc -threads (по умолчанию: число ядер; в bspc максимум 64, больше - потоки ломаются)",
        "help.no_aas_optimize": "без bspc -optimize (быстрее фаза AAS; больше .aas - только сжатие данных, reachability тот же)",
        "help.aas_geometry_fast": "как --aas-bspc-nocsg --aas-bspc-freetree (быстрее, грубее коллизии)",
        "help.aas_bspc_nocsg": "передать bspc -nocsg: без ChopBrushes/CSG (быстрее; пересечения солидов - хуже AAS)",
        "help.aas_bspc_freetree": "передать bspc -freetree: раньше освободить BSP-дерево (память; чуть быстрее на огромных картах)",
        "help.aas_bspc_breadthfirst": "передать bspc -breadthfirst: обход BSP в ширину (эффект сильно зависит от карты)",
        "help.bspc_concurrent": "одновременных процессов bspc (по умолчанию: 1; 0 = лимит min(задачи, max(32,cpu*4)), не --coworkers)",
        "help.force": "перезаписывать вывод; вместе с --skip-mapless - всё равно обрабатывать pk3 без .bsp",
        "help.coworkers": "параллельных задач pk3 (пул может быть больше при очереди bspc)",
        "help.pool_max": "верхняя граница пула потоков при лимите bspc (по умолчанию: 96; макс. 512)",
        "help.workshop": "id предметов мастерской steam",
        "help.collection": "id страниц коллекций steam. для вывода используйте -o кат; не ставьте каталог сразу после --collection. не числа: пути или вывод.",
        "help.optimize": "jpeg для текстур где безопасно",
        "help.bsp_patch_method": "способ патча entities (1 или 2)",
        "help.bspc": "путь к bspc.exe",
        "help.levelshot": "картинка levelshot по умолчанию",
        "help.steamcmd": "steamcmd.exe для загрузки из мастерской",
        "help.ffmpeg": "ffmpeg для ogg -> wav (q3 использует wav)",
        "help.verbose": "подробный лог (в т.ч. stderr bspc); строки пропусков по файлам",
        "help.show_skipped": "печатать каждый пропущенный pk3; как у --verbose",
        "help.hide_converted": "не печатать ok по каждому файлу",
        "help.skip_mapless": "пропускать pk3 без .bsp в архиве (поиск по всему дереву); с --force обработать и такие",
        "help.time_stages": "суммарное время по фазам в сводке",
        "help.dry_run": "список действий без конвертации",
        "help.no_color": "без ansi (также no_color)",
        "help.no_progress": "без tqdm; только текст (gui так передаёт прогресс по qltoq3_progress)",
        "help.log": "дописать лог сессии в файл (без ansi)",
        "help.ql_pak": "путь к оригинальному pak00.pk3 из quake live (по умолчанию: <repo>/ql_baseq3/pak00.pk3)",
        "cfg.col.setting": "параметр",
        "cfg.col.value": "значение",
        "cfg.title": "конфигурация запуска",
        "cfg.output": "вывод",
        "cfg.pk3_files": "файлов pk3",
        "cfg.coworkers": "coworkers",
        "cfg.pool": "пул",
        "cfg.pool_max": "pool-max",
        "cfg.force": "force",
        "cfg.yes_always": "yes-always",
        "cfg.optimize_jpg": "optimize (jpg)",
        "cfg.bsp_patch_method": "bsp-patch-method",
        "cfg.no_aas": "no-aas",
        "cfg.aas_timeout": "aas-timeout",
        "cfg.aas_threads": "aas-threads",
        "cfg.aas_threads_note": "{n} (effective; bspc -threads)",
        "cfg.bspc_concurrent": "bspc-concurrent",
        "cfg.bspc_unlimited": "без лимита",
        "cfg.bspc": "bspc",
        "cfg.levelshot": "levelshot",
        "cfg.ffmpeg": "ffmpeg",
        "cfg.steamcmd": "steamcmd",
        "cfg.verbose": "verbose",
        "cfg.show_skipped": "show-skipped",
        "cfg.hide_converted": "hide-converted",
        "cfg.skip_mapless": "skip-mapless",
        "cfg.dry_list": "dry-run / list",
        "cfg.colors": "цвета терминала",
        "cfg.ql_pak00": "ql pak00",
        "cfg.pak00_missing": "не задан или файл не найден",
        "cfg.pak00_sha": "pak00 sha-256",
        "cfg.pak00_no_ref": "нет эталонного хэша; проверка не делалась",
        "cfg.pak00_no_ref_bundled": "нет эталонного хэша (bundled/expected_pak00.sha256)",
        "cfg.pak00_ref_no_ql": "эталон есть; --ql-pak не задан",
        "cfg.pak00_match": "совпадает с эталоном",
        "cfg.pak00_mismatch": "не совпадает с эталоном (не оригинал?)",
        "cfg.log_file": "лог-файл",
        "cfg.workshop": "workshop",
        "cfg.collection": "collection",
        "cfg.yes": "да",
        "cfg.no": "нет",
        "stats.col.metric": "метрика",
        "stats.col.value": "значение",
        "stats.time": "прошло времени",
        "stats.seconds": "{t:.2f} с",
        "stats.paks_done": "обработано pak",
        "stats.skipped": "пропущено",
        "stats.skipped_detail": "{n} (есть: {ex}, q3: {q3}, без карт: {nm})",
        "stats.maps": "карт пропатчено",
        "stats.images": "картинок конвертировано",
        "stats.sounds": "звуков (ogg -> wav)",
        "stats.restored": "восстановлено ресурсов",
        "stats.phase": "фаза {key}",
        "stats.pak00_integrity": "целостность pak00",
        "stats.pak00_bad": "sha-256 не совпадает с эталоном (возможно не оригинальный ql pak00)",
        "stats.done": "готово за {t}",
        "stats.hint_all_q3_compat": "ничего не записано: часть pk3 пропущена как \"уже как q3\". для конвертации укажите --force.",
        "stats.hint_skip_mapless": "ничего не записано: часть pk3 пропущена из-за --skip-mapless (в архиве не найден .bsp). уберите --skip-mapless или добавьте --force.",
        "stats.hint_failures": "один или несколько pk3 завершились с ошибкой (строки выше). полный стек: --verbose.",
        "stats.hint_nothing_written": "ничего не записано (нет успешных конвертаций). если ожидался вывод - смотрите ошибки выше и пути.",
        "dry.title": "пробный прогон - ничего не записано",
        "dry.out": "вывод:",
        "dry.q3_compat": "q3-совместим:",
        "dry.exists": "есть:",
        "dry.skip_exists": "пропуск (вывод уже есть)",
        "dry.skip_compat": "пропуск (уже q3-совместим)",
        "dry.would_convert": " -> будет конвертация",
        "lim.title": "ограничения / что пропущено",
        "lim.no_index": "  - assets_index.json: нет по пути {path}. индекс ql/q3 недоступен; подбор ресурсов пропущен.",
        "lim.no_pak00": "  - pak00.pk3: --ql-pak не задан или файл не найден. файлы только из ql не восстанавливались из pak00.",
        "lim.no_bspc": "  - bspc: не найден ({path}). генерация aas (bsp2aas) не запускалась.",
        "lim.no_ffmpeg": "  - ffmpeg: не найден ({path}). ogg -> wav не выполнялся.",
        "lim.pak00_hash": "  - pak00.pk3: sha-256 не совпадает с эталоном. возможно не официальный pak; ресурсы могут отличаться.",
        "warn.title": "внимание",
        "warn.no_pak": "  путь к pak00 не задан (--ql-pak) или файл не найден.",
        "warn.no_pak2": "  ресурсы только из ql не копируются в выходной pk3.",
        "warn.bad_hash": "  sha-256 pak00.pk3 != эталону в репозитории.",
        "warn.bad_hash2": "  возможно не оригинальный pak; ресурсы могут быть неверны.",
        "err.index_missing": "не найден assets_index.json: {path}",
        "issue.title": "проблемы",
        "prog.overall": "общий прогресс",
        "prog.coworker_idle": "< поток #{n} простаивает >",
        "prog.bspc_queue": "очередь bspc: {n} ждут",
        "aas.global": "aas (глобально)",
        "aas.waiting": "ожидание",
        "interrupt.aas": "прервано на глобальной фазе aas.",
        "interrupt.ctrlc": "прервано (ctrl+c). очередь отменена; докручиваются текущие pk3.",
        "interrupt.partial": "прервано - итоги частичные (не все pk3 готовы).",
        "pk3.skip_exists": "пропуск (уже есть): {fn}",
        "pk3.skip_compat": "внимание: {fn} уже совместим.",
        "pk3.skip_mapless": "пропуск (нет карт): {fn}",
        "pk3.extract": "распаковка",
        "pk3.patch_bsps": "патч bsp",
        "pk3.shaders": "шейдеры",
        "pk3.models": "модели",
        "pk3.images": "картинки",
        "pk3.restore": "восстановление ql",
        "pk3.repack": "упаковка",
        "pk3.res_prefix": "рес=",
        "pk3.ok": "ok {fn} за {sec} с",
        "chk.root": "корень assets_index.json должен быть объектом",
        "chk.sides": "assets_index.json должен содержать 'ql' и 'q3'",
        "chk.side_obj": "assets_index.json['{side}'] должен быть объектом",
        "chk.files_shaders": "assets_index.json['{side}'] должен содержать '{subkey}'",
    },
)

_merge(
    "ru",
    {
        "gui.title": "qltoq3",
        "gui.tab_sources": "источники",
        "gui.tab_settings": "настройки",
        "gui.tab_dependencies": "зависимости",
        "gui.tab_updates": "обновления",
        "gui.tab_logs": "логи",
        "gui.lang_short": "язык",
        "gui.out_folder": "папка вывода (сюда попадут сконвертированные pk3)",
        "gui.browse": "обзор",
        "gui.local_drop_hint": "вы можете перетащить файлы или папки сюда",
        "gui.open_output": "открыть вывод",
        "gui.open_output_failed": "не удалось открыть папку вывода: {error}",
        "gui.pk3_sources": "pk3 и папки на этом компьютере",
        "gui.add_files": "добавить файлы...",
        "gui.add_dir": "добавить папку...",
        "gui.tip_remove": "удалить выбранные строки из списка",
        "gui.tip_clear": "очистить весь список",
        "gui.tip_add_files": "добавить один или несколько .pk3",
        "gui.tip_add_dir": "добавить папку (поиск pk3 внутри)",
        "gui.tip_browse_out": "выбрать папку вывода",
        "gui.log": "лог вывода",
        "gui.log_empty": "лог пуст.",
        "gui.log_copied": "лог скопирован.",
        "gui.log_saved": "лог сохранен.",
        "gui.log_save_failed": "не удалось сохранить лог: {error}",
        "gui.log_hint": "только чтение; полная командная строка дублируется в начале при запуске",
        "gui.run": "запуск",
        "gui.stop": "стоп",
        "gui.clear_log": "очистить лог",
        "gui.copy_log": "скопировать",
        "gui.save_log": "сохранить в файл",
        "gui.running": "выполняется...",
        "gui.done_ok": "готово за {t} (код {code})",
        "gui.done_err": "ошибка за {t} (код {code})",
        "gui.stopped": "остановлено",
        "gui.stopped_elapsed": "остановлено - {t}",
        "gui.err_paths": "ошибка пути: локальный pk3/папка, id мастерской или коллекции.",
        "gui.err_output": "укажите папку вывода.",
        "gui.header_behavior": "опции конвертации",
        "gui.header_parallelism": "параллелизм и пути ботов",
        "gui.mode_local": "локальные файлы",
        "gui.mode_steam": "мастерская steam",
        "gui.workshop_ids": "id предметов",
        "gui.collection_ids": "id коллекций",
        "gui.add": "добавить",
        "gui.opt.yes_always": "ничего не спрашивать, пропуск подтверждений",
        "gui.opt.force": "перезаписывать файлы, которые уже есть в папке вывода",
        "gui.opt.no_aas": "не строить сетку навигации для ботов (быстрее; на картах боты могут не работать)",
        "gui.opt.optimize": "сжимать текстуры в jpeg там, где это безопасно",
        "gui.opt.dry_run": "ничего не делать, предпросмотр работы",
        "gui.opt.hide_converted": "короче лог: не показывать ok по каждому файлу",
        "gui.opt.skip_mapless": "пропускать паки, в которых нет карты",
        "gui.opt.verbose": "подробный лог: больше сообщений о ходе работы",
        "gui.opt.show_skipped": "в логе перечислять каждый пропущенный пак по имени",
        "gui.opt.time_stages": "в конце показать, сколько занял каждый этап",
        "gui.opt.no_aas_optimize": "aas: без bspc -optimize (быстрее; больше .aas)",
        "gui.opt.aas_geometry_fast": "aas: быстрее/грубее bspc (как --aas-geometry-fast)",
        "gui.opt.aas_bspc_breadthfirst": "aas: bspc breadth-first (если зависает на огромных картах)",
        "gui.opt.bsp_patch": "метод конверсии карт (1 - костыльный, 2 - долгий)",
        "gui.num.coworkers": "сколько паков обрабатывать одновременно",
        "gui.num.pool_max": "максимум потоков",
        "gui.num.aas_timeout": "сколько секунд тратить на генерацию путей для ботов",
        "gui.num.bspc_concurrent": "сколько карт готовить для ботов параллельно",
        "gui.num.aas_threads": "потоки cpu на одну карту (пусто = авто)",
        "gui.path.bspc": "компилятор карт (bspc.exe)",
        "gui.path.levelshot": "левелшот по умолчанию",
        "gui.path.steamcmd": "steamcmd (загрузка из мастерской)",
        "gui.path.ffmpeg": "ffmpeg (перегон звуков в wav)",
        "gui.path.ql_pak": "оригинальный pak00.pk3 из quake live",
        "gui.extra_log": "дополнительно писать лог сессии в файл",
        "gui.placeholder_auto": "авто",
        "gui.log_path_ph": "необязательный путь к файлу лога...",
        "gui.credit": "by q3unite.su",
        "gui.reset": "сбросить настройки",
        "gui.section_activity": "ход работы",
        "gui.elapsed": "прошло {t}",
        "gui.progress_starting": "запуск...",
        "gui.progress_packs": "пак {cur} из {total}: {name}",
        "gui.progress_action": "операция: {action}",
        "gui.phase_deferred": "отложенная фаза bot-path ({n} карт в очереди)...",
        "gui.out_pick_title": "выбор папки вывода",
        "gui.out_not_dir_title": "некорректный путь вывода",
        "gui.out_not_dir_msg": "путь существует, но это не папка:\n{path}\n\nвыберите другую папку вывода.",
        "gui.out_missing_title": "папка вывода не найдена",
        "gui.out_missing_msg": "папка вывода не существует:\n{path}\n\nсоздать её?",
        "gui.out_mkdir_fail_title": "не удалось создать папку",
        "gui.out_mkdir_fail_msg": "не удалось создать папку:\n{path}\n\n{error}\n\nвыбрать другую папку вывода?",
        "gui.out_nowrite_title": "нет прав на запись",
        "gui.out_nowrite_msg": "нет прав на запись в папку:\n{path}\n\n{error}\n\nвыбрать другую папку вывода?",
        "gui.out_canceled": "процесс отменен пользователем.",
        "gui.out_retry_hint": "выберите другую папку вывода и запустите снова.",
        "gui.ws_id_invalid": "введите корректный id предмета или ссылку steam.",
        "gui.col_id_invalid": "введите корректный id коллекции или ссылку steam.",
        "gui.tmp_found_title": "найдены временные папки",
        "gui.tmp_found_msg": "найдены временные папки qltoq3 от прошлых запусков: {n}.\n\nудалить сейчас?",
        "gui.tmp_removed": "временные папки удалены: {n}.",
        "gui.tmp_kept": "временные папки оставлены.",
        "gui.tmp_remove_failed": "не удалось удалить временные папки: {n}.",
        "gui.opt.check_updates_on_start": "проверять обновления при запуске",
        "gui.opt.auto_download_update": "пытаться скачивать обновления автоматически",
        "gui.header_updates": "обновления",
        "gui.update_check_now": "проверить обновления сейчас",
        "gui.update_current_label": "текущая",
        "gui.update_latest_label": "доступная",
        "gui.update_checking": "проверка обновлений...",
        "gui.update_check_failed": "не удалось проверить обновления.",
        "gui.update_none": "у вас уже последняя версия.",
        "gui.update_title": "доступно обновление",
        "gui.update_available_msg": "доступна новая версия.\n\nтекущая: {current}\nновая: {latest}\n\nоткрыть страницу скачивания?",
        "gui.update_available_status": "доступно обновление: {latest}",
        "gui.update_auto_installed_only": "автообновление работает только для установленной версии.",
        "gui.update_download_failed": "не удалось скачать обновление.",
        "gui.update_integrity_missing": "не найден файл проверки целостности обновления.",
        "gui.update_integrity_failed": "проверка хэша файла обновления не пройдена.",
        "gui.update_deferred": "обновление {latest} готово. установка начнется после конвертации.",
        "gui.update_silent_start": "установка обновления {latest}...",
        "gui.update_run_failed": "не удалось запустить установщик: {error}",
        "gui.path_status_empty": "путь не задан.",
        "gui.path_status_missing": "путь не найден.",
        "gui.path_status_need_file": "нужен файл, а не папка.",
        "gui.path_status_need_dir": "нужна папка, а не файл.",
        "gui.path_status_ok": "путь найден.",
        "tmp.found": "найдены временные папки qltoq3 от прошлых запусков: {n}.",
        "tmp.ask_remove": "удалить их сейчас? [y/N]: ",
        "tmp.removed": "временные папки удалены: {n}.",
        "tmp.kept": "временные папки оставлены.",
        "tmp.noninteractive_skip": "найдены временные папки ({n}); неинтерактивный режим, папки оставлены.",
        "tmp.remove_failed": "не удалось удалить временные папки: {n}.",
    },
)


def _candidate_locales_dirs() -> list[Path]:
    out: list[Path] = []
    env_dir = (os.environ.get("QLTOQ3_LOCALES_DIR") or "").strip()
    if env_dir:
        out.append(Path(env_dir).expanduser())
    if getattr(sys, "frozen", False):
        out.append(Path(sys.executable).resolve().parent / "locales")
    out.append(Path(__file__).resolve().parents[1] / "locales")
    dedup: list[Path] = []
    seen: set[str] = set()
    for p in out:
        k = str(p.resolve()) if p.exists() else str(p)
        if k in seen:
            continue
        seen.add(k)
        dedup.append(p)
    return dedup


def _flatten_locale_dict(d: dict[str, object]) -> dict[str, str]:
    if "strings" in d and isinstance(d["strings"], dict):
        d = d["strings"]  # type: ignore[assignment]
    out: dict[str, str] = {}
    for k, v in d.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


def _load_external_locales() -> None:
    for lang in ("en", "ru"):
        for base in _candidate_locales_dirs():
            fp = base / f"{lang}.toml"
            if not fp.is_file():
                continue
            try:
                raw = tomllib.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            ext = _flatten_locale_dict(raw)
            if ext:
                _merge(lang, ext)


_load_external_locales()


def _prefs_file() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return Path(base) / "qltoq3" / "prefs.json"
    return Path.home() / ".config" / "qltoq3" / "prefs.json"


def _lang_from_prefs() -> str | None:
    fp = _prefs_file()
    if not fp.is_file():
        return None
    try:
        raw = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    lang = str(raw.get("lang", "")).strip().lower()
    if lang in ("en", "ru"):
        return lang
    return None


def default_lang_from_env() -> str:
    direct = (os.environ.get("QLTOQ3_LANG") or "").strip().lower()
    if direct in ("en", "ru"):
        return direct
    pref = _lang_from_prefs()
    if pref is not None:
        return pref
    v = (os.environ.get("LANG") or "en").strip().lower().replace("_", "-")
    if v.startswith("ru"):
        return "ru"
    return "en"


def lang_from_argv(argv: list[str]) -> str:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument(
        "--lang",
        choices=["en", "ru"],
        default=default_lang_from_env(),
    )
    return p.parse_known_args(argv)[0].lang


def set_lang(code: str) -> None:
    global _LANG
    _LANG = code if code in S else "en"


def get_lang() -> str:
    return _LANG


def tr(key: str, **kwargs: object) -> str:
    d = S.get(_LANG) or S["en"]
    s = d.get(key)
    if s is None:
        s = S["en"].get(key, key)
    if kwargs:
        return s.format(**kwargs)
    return s
