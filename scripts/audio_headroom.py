#!/usr/bin/env python3
from __future__ import annotations

import argparse
import struct
import wave
from pathlib import Path

TARGET_PEAK = 29000


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply safe headroom to 16-bit PCM narration WAV.")
    p.add_argument("wav", type=Path)
    p.add_argument("--target-peak", type=int, default=TARGET_PEAK)
    return p.parse_args()


def apply_headroom(path: Path, target_peak: int) -> dict:
    path = path.expanduser().resolve()
    with wave.open(str(path), "rb") as src:
        params = src.getparams()
        raw = src.readframes(src.getnframes())

    if params.sampwidth != 2:
        raise SystemExit(f"16-bit PCM WAV only: sample_width={params.sampwidth}")

    if not raw:
        raise SystemExit("WAV is empty")

    values = list(struct.unpack("<" + "h" * (len(raw) // 2), raw))
    peak = max(abs(v) for v in values)
    if peak <= 0:
        return {"changed": False, "beforePeak": peak, "afterPeak": peak, "gain": 1.0}

    if peak <= target_peak:
        return {"changed": False, "beforePeak": peak, "afterPeak": peak, "gain": 1.0}

    gain = target_peak / peak
    scaled = [max(-32768, min(32767, int(round(v * gain)))) for v in values]
    packed = struct.pack("<" + "h" * len(scaled), *scaled)

    temp = path.with_suffix(".headroom.tmp.wav")
    with wave.open(str(temp), "wb") as dst:
        dst.setparams(params)
        dst.writeframes(packed)
    temp.replace(path)

    after_peak = max(abs(v) for v in scaled)
    return {
        "changed": True,
        "beforePeak": peak,
        "afterPeak": after_peak,
        "gain": round(gain, 6),
    }


def main() -> int:
    args = parse_args()
    result = apply_headroom(args.wav, args.target_peak)
    print(
        "narration headroom: "
        f"before={result['beforePeak']} after={result['afterPeak']} gain={result['gain']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
