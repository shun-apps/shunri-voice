#!/usr/bin/env python3
from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 48000


def _clamp16(value: float) -> int:
    return max(-32768, min(32767, int(round(value))))


def _fade_gain(t: float, duration: float, fade: float = 0.65) -> float:
    if duration <= 0:
        return 0.0
    if t < fade:
        return max(0.0, min(1.0, t / fade))
    if t > duration - fade:
        return max(0.0, min(1.0, (duration - t) / fade))
    return 1.0


def _write_pcm16_mono(path: Path, samples: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(struct.pack("<" + "h" * len(samples), *samples))


def generate_ambient_bgm(path: Path, duration: float) -> Path:
    count = max(1, int(duration * SAMPLE_RATE))
    rng = random.Random(5601)
    samples: list[int] = []

    # Understated original ambient bed: low harmonic drone + slow pulse.
    freqs = (110.0, 164.81, 220.0)
    phases = (0.0, 0.9, 1.7)

    for n in range(count):
        t = n / SAMPLE_RATE
        lfo = 0.72 + 0.28 * math.sin(2 * math.pi * 0.11 * t)
        value = 0.0
        for idx, freq in enumerate(freqs):
            value += math.sin(2 * math.pi * freq * t + phases[idx]) * (150.0 - idx * 28.0)

        # Soft editorial pulse every ~2 seconds. No repetitive whoosh.
        pulse_phase = t % 2.0
        if pulse_phase < 0.18:
            env = math.exp(-pulse_phase * 25.0)
            value += math.sin(2 * math.pi * 55.0 * t) * 620.0 * env

        value += (rng.random() - 0.5) * 18.0
        value *= lfo * _fade_gain(t, duration)
        samples.append(_clamp16(value))

    _write_pcm16_mono(path, samples)
    return path


def _add_pop(samples: list[float], at: float, amplitude: float = 2300.0) -> None:
    start = int(max(0.0, at) * SAMPLE_RATE)
    length = int(0.16 * SAMPLE_RATE)
    for i in range(length):
        pos = start + i
        if pos >= len(samples):
            break
        t = i / SAMPLE_RATE
        env = math.exp(-t * 25.0)
        freq = 620.0 + 520.0 * min(1.0, t / 0.08)
        samples[pos] += math.sin(2 * math.pi * freq * t) * amplitude * env


def _add_impact(samples: list[float], at: float, amplitude: float = 2600.0) -> None:
    start = int(max(0.0, at) * SAMPLE_RATE)
    length = int(0.20 * SAMPLE_RATE)
    for i in range(length):
        pos = start + i
        if pos >= len(samples):
            break
        t = i / SAMPLE_RATE
        env = math.exp(-t * 20.0)
        value = (
            math.sin(2 * math.pi * 90.0 * t) * 0.75
            + math.sin(2 * math.pi * 180.0 * t) * 0.25
        )
        samples[pos] += value * amplitude * env


def _add_click(samples: list[float], at: float, amplitude: float = 1900.0) -> None:
    start = int(max(0.0, at) * SAMPLE_RATE)
    length = int(0.09 * SAMPLE_RATE)
    for i in range(length):
        pos = start + i
        if pos >= len(samples):
            break
        t = i / SAMPLE_RATE
        env = math.exp(-t * 45.0)
        samples[pos] += math.sin(2 * math.pi * 900.0 * t) * amplitude * env


def generate_sfx(path: Path, duration: float, scenes: list[dict]) -> Path:
    count = max(1, int(duration * SAMPLE_RATE))
    samples = [0.0] * count

    for scene in scenes:
        start = float(scene.get("start", 0.0))
        scene_type = str(scene.get("type") or "")
        camera = str(scene.get("cameraMotion") or scene.get("motion") or "")

        if scene_type == "talk_overlay" or scene.get("overlay"):
            _add_pop(samples, start + 0.10)
        elif scene_type == "cta":
            _add_click(samples, start + 0.06)
        elif "punch" in camera:
            _add_impact(samples, start + 0.04, amplitude=1700.0)

    _write_pcm16_mono(path, [_clamp16(v) for v in samples])
    return path


def generate_audio_tracks(job_dir: Path, duration: float, scenes: list[dict]) -> tuple[Path, Path]:
    bgm = generate_ambient_bgm(job_dir / "auto-bgm.wav", duration)
    sfx = generate_sfx(job_dir / "auto-sfx.wav", duration, scenes)
    return bgm, sfx
