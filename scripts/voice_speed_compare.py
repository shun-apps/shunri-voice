#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT
    / "outputs"
    / "gemini-voice-younger-candidates"
    / "03-shunri-warm-younger-c-audition.wav"
)
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "gemini-voice-speed-compare"
RENDER_IMAGE = "shunri-reel-renderer:local"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Create exact-speed audition variants for the selected Shunri voice."
    )
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--rates", nargs="+", type=float, default=[1.2, 1.3])
    return p.parse_args()


def ensure_docker() -> None:
    if shutil.which("docker") is None:
        raise SystemExit("Docker CLI が見つかりません。")
    proc = subprocess.run(
        ["docker", "image", "inspect", RENDER_IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"{RENDER_IMAGE} がありません。先に make reel-renderer-setup を実行してください。"
        )


def render_variant(source: Path, dest: Path, rate: float) -> None:
    work = dest.parent.resolve()
    source_copy = work / "source.wav"
    shutil.copy2(source, source_copy)
    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{work}:/work",
            RENDER_IMAGE,
            "-y",
            "-i", "/work/source.wav",
            "-filter:a", f"atempo={rate:.3f}",
            "-ar", "48000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            f"/work/{dest.name}",
        ],
        check=True,
    )


def main() -> int:
    args = parse_args()
    source = args.input.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"選択音声が見つかりません: {source}")

    rates = []
    for rate in args.rates:
        if not 0.5 <= rate <= 2.0:
            raise SystemExit(f"atempo対応範囲外です: {rate}")
        rates.append(rate)

    ensure_docker()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Selected voice: Shunri Warm Younger C (#3)")
    print(f"source: {source}")
    for rate in rates:
        tag = str(rate).replace(".", "p")
        dest = output_dir / f"shunri-warm-younger-c-{tag}x.wav"
        print(f"render: {rate:.2f}x -> {dest.name}")
        render_variant(source, dest, rate)

    source_copy = output_dir / "source.wav"
    if source_copy.exists():
        source_copy.unlink()

    print()
    print("Speed comparison created.")
    for rate in rates:
        tag = str(rate).replace(".", "p")
        dest = output_dir / f"shunri-warm-younger-c-{tag}x.wav"
        print(f"  afplay {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
