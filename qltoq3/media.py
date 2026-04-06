"""dds/png/ogg in map folder."""

import os
import subprocess

from PIL import Image

from . import md3


def convert_image(filepath, optimize=False):
    try:
        with Image.open(filepath) as img:
            has_alpha = img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            )
            base_path = os.path.splitext(filepath)[0]
            if optimize and not has_alpha:
                img.convert("RGB").save(base_path + ".jpg", format="JPEG", quality=90)
            else:
                img.save(base_path + ".tga", format="TGA")
        os.remove(filepath)
        return True, None
    except Exception as e:
        return False, f"Image error in {os.path.basename(filepath)}: {str(e)}"


def ogg2wav(filepath, ffmpeg_bin="ffmpeg"):
    base = os.path.splitext(filepath)[0]
    wav_path = base + ".wav"
    try:
        r = subprocess.run(
            [
                ffmpeg_bin,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                filepath,
                "-acodec",
                "pcm_s16le",
                "-ar",
                "22050",
                "-ac",
                "1",
                wav_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        if r.returncode != 0:
            err = (
                r.stderr.decode("utf-8", errors="replace").strip()
                or f"exit {r.returncode}"
            )
            return False, f"ffmpeg OGG->WAV {os.path.basename(filepath)}: {err}"
        os.remove(filepath)
        return True, None
    except FileNotFoundError:
        return (
            False,
            f"ffmpeg not found ({ffmpeg_bin}); install ffmpeg or pass --ffmpeg",
        )
    except Exception as e:
        return False, f"OGG error in {os.path.basename(filepath)}: {str(e)}"


def fix_all_models(root: str) -> int:
    n = 0
    for dirname, _, files in os.walk(root):
        for f in files:
            if not f.lower().endswith(".md3"):
                continue
            md3.md3_tex(os.path.join(dirname, f))
            n += 1
    return n


def convert_all_images(root: str, optimize: bool = False) -> int:
    n = 0
    for dirname, _, files in os.walk(root):
        for f in files:
            low = f.lower()
            if low.endswith(".dds") or low.endswith(".png"):
                ok, _ = convert_image(os.path.join(dirname, f), optimize=optimize)
                if ok:
                    n += 1
    return n


def convert_all_ogg_to_wav(root: str, ffmpeg_bin: str = "ffmpeg") -> int:
    n = 0
    for dirname, _, files in os.walk(root):
        for f in files:
            if not f.lower().endswith(".ogg"):
                continue
            ok, _ = ogg2wav(os.path.join(dirname, f), ffmpeg_bin=ffmpeg_bin)
            if ok:
                n += 1
    return n
