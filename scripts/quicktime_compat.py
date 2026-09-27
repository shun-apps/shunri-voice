#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER_IMAGE = "shunri-reel-renderer:local"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create a QuickTime-compatible playback copy.")
    p.add_argument("source", type=Path)
    p.add_argument("--output", type=Path)
    return p.parse_args()


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, text=True)


def avconvert_presets() -> str:
    tool = Path("/usr/bin/avconvert")
    if not tool.exists():
        return ""
    proc = subprocess.run(
        [str(tool), "--listPresets"],
        capture_output=True,
        text=True,
        check=False,
    )
    return (proc.stdout or "") + "\n" + (proc.stderr or "")


def try_avconvert(source: Path, output: Path) -> bool:
    if platform.system() != "Darwin":
        return False

    tool = Path("/usr/bin/avconvert")
    if not tool.exists():
        return False

    presets = avconvert_presets()
    candidates = [
        "PresetAppleM4V720pHD",
        "AppleM4V720pHD",
        "PresetAppleM4VAppleTV",
        "AppleM4VAppleTV",
    ]
    available = [name for name in candidates if name in presets]
    if not available:
        available = candidates

    for preset in available:
        output.unlink(missing_ok=True)
        proc = subprocess.run(
            [
                str(tool),
                "--preset", preset,
                "--source", str(source),
                "--output", str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and output.exists() and output.stat().st_size > 100_000:
            print(f"QuickTime copy: Apple avconvert / {preset}")
            return True

    return False


def docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    proc = subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


def fallback_ffmpeg(source: Path, output: Path) -> None:
    if not docker_ready():
        raise SystemExit("Apple avconvertに失敗し、Docker fallbackも利用できません。")

    work = output.parent.resolve()
    source_copy = work / ("qt-source" + source.suffix.lower())
    if source.resolve() != source_copy.resolve():
        shutil.copy2(source, source_copy)

    output.unlink(missing_ok=True)
    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{work}:/work",
            RENDER_IMAGE,
            "-y",
            "-fflags", "+genpts",
            "-i", f"/work/{source_copy.name}",
            "-vf",
            "scale=720:1280:force_original_aspect_ratio=decrease,"
            "pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,"
            "format=yuv420p",
            "-r", "30",
            "-vsync", "cfr",
            "-c:v", "libx264",
            "-profile:v", "main",
            "-level:v", "3.1",
            "-tag:v", "avc1",
            "-preset", "medium",
            "-crf", "21",
            "-c:a", "aac",
            "-profile:a", "aac_low",
            "-ar", "48000",
            "-ac", "2",
            "-b:a", "160k",
            "-avoid_negative_ts", "make_zero",
            "-video_track_timescale", "30000",
            "-movflags", "+faststart",
            f"/work/{output.name}",
        ],
        check=True,
    )
    print("QuickTime copy: ffmpeg strict H.264/AAC compatibility fallback")


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"sourceがありません: {source}")

    output = (
        args.output.expanduser().resolve()
        if args.output
        else source.with_name(source.stem + "-quicktime.m4v")
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    if not try_avconvert(source, output):
        fallback_ffmpeg(source, output)

    print(f"QuickTime-compatible copy: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
