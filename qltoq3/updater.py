from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

LATEST_RELEASE_URL = "https://api.github.com/repos/unite-q3-team/QLtoQ3/releases/latest"
SETUP_ASSET_RE = re.compile(r"qltoq3-setup-.*-win64\.exe$", re.IGNORECASE)


@dataclass
class ReleaseInfo:
    latest_version: str
    html_url: str
    asset_name: str | None
    asset_url: str | None
    sha256_url: str | None


def version_tuple(v: str) -> tuple[int, ...]:
    s = (v or "").strip().lower()
    if s.startswith("v"):
        s = s[1:]
    parts: list[int] = []
    for chunk in s.split("."):
        m = re.match(r"(\d+)", chunk)
        parts.append(int(m.group(1)) if m else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer_version(latest: str, current: str) -> bool:
    return version_tuple(latest) > version_tuple(current)


def find_release_setup_asset(
    assets: list[dict[str, object]],
) -> tuple[str | None, str | None]:
    for asset in assets:
        name = str(asset.get("name", ""))
        url = str(asset.get("browser_download_url", ""))
        if name and url and SETUP_ASSET_RE.search(name):
            return name, url
    for asset in assets:
        name = str(asset.get("name", ""))
        url = str(asset.get("browser_download_url", ""))
        if name.lower().endswith(".exe") and url:
            return name, url
    return None, None


def find_sha_asset_url(
    assets: list[dict[str, object]], primary_asset_name: str | None
) -> str | None:
    if primary_asset_name:
        exact = f"{primary_asset_name}.sha256"
        for asset in assets:
            name = str(asset.get("name", ""))
            url = str(asset.get("browser_download_url", ""))
            if name == exact and url:
                return url
    for asset in assets:
        name = str(asset.get("name", "")).lower()
        url = str(asset.get("browser_download_url", ""))
        if name.endswith(".sha256") and "setup" in name and url:
            return url
    return None


def fetch_latest_release(timeout_sec: int = 12) -> ReleaseInfo | None:
    req = urllib.request.Request(
        LATEST_RELEASE_URL,
        headers={"User-Agent": "QLtoQ3-Updater"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    latest = str(raw.get("tag_name") or "").strip()
    if not latest:
        return None
    html_url = str(raw.get("html_url") or "").strip()
    assets_raw = raw.get("assets", [])
    if not isinstance(assets_raw, list):
        assets_raw = []
    assets = [a for a in assets_raw if isinstance(a, dict)]
    asset_name, asset_url = find_release_setup_asset(assets)
    sha_url = find_sha_asset_url(assets, asset_name)
    return ReleaseInfo(
        latest_version=latest,
        html_url=html_url,
        asset_name=asset_name,
        asset_url=asset_url,
        sha256_url=sha_url,
    )


def download_file(url: str, dst: Path, timeout_sec: int = 30) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "QLtoQ3-Updater"})
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        data = resp.read()
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)


def read_sha256_from_file(sha_file: Path) -> str | None:
    try:
        content = sha_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = re.search(r"\b([A-Fa-f0-9]{64})\b", content)
    return m.group(1).lower() if m else None


def calc_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def verify_sha256(payload_path: Path, expected_hex: str) -> bool:
    if not expected_hex:
        return False
    return calc_sha256(payload_path) == expected_hex.lower()


def is_installed_mode(executable_path: Path) -> bool:
    app_dir = executable_path.resolve().parent
    return (app_dir / "unins000.exe").is_file()
