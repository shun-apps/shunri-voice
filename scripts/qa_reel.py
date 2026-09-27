#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER_IMAGE = "shunri-reel-renderer:local"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate a rendered Shunri Reel.")
    p.add_argument("--video", required=True, type=Path)
    p.add_argument("--narration", required=True, type=Path)
    p.add_argument("--scene-plan", required=True, type=Path)
    p.add_argument("--captions", required=True, type=Path)
    p.add_argument("--script-file", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    return p.parse_args()


def wav_stats(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        rate = wav.getframerate()
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        count = wav.getnframes()
        raw = wav.readframes(count)

    duration = count / rate if rate else 0.0
    peak = 0
    rms = 0.0

    if width == 2 and raw:
        values = struct.unpack("<" + "h" * (len(raw) // 2), raw)
        if channels > 1:
            mono = []
            for i in range(0, len(values), channels):
                chunk = values[i : i + channels]
                mono.append(sum(chunk) / len(chunk))
            values = tuple(mono)
        peak = max(abs(int(v)) for v in values) if values else 0
        rms = (sum(float(v) * float(v) for v in values) / max(1, len(values))) ** 0.5

    return {
        "duration": duration,
        "peak": peak,
        "rms": rms,
        "sampleRate": rate,
        "channels": channels,
    }


def ffprobe(path: Path) -> dict:
    parent = path.parent.resolve()
    proc = subprocess.run(
        [
            "docker", "run", "--rm",
            "--entrypoint", "ffprobe",
            "-v", f"{parent}:/work:ro",
            RENDER_IMAGE,
            "-hide_banner",
            "-loglevel", "error",
            "-show_streams",
            "-show_format",
            "-of", "json",
            f"/work/{path.name}",
        ],
        executable="docker",
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ffprobe failed")
    return json.loads(proc.stdout)


def parse_ass_time(value: str) -> float:
    h, m, s = value.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def caption_windows(path: Path) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 3:
            continue
        result.append((parse_ass_time(parts[1]), parse_ass_time(parts[2])))
    return result


def decode_test(path: Path) -> tuple[bool, str]:
    parent = path.parent.resolve()
    proc = subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{parent}:/work:ro",
            RENDER_IMAGE,
            "-v", "error",
            "-i", f"/work/{path.name}",
            "-map", "0:v:0",
            "-map", "0:a:0?",
            "-f", "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0, (proc.stderr or "").strip()


def caption_entries(path: Path) -> list[dict]:
    entries: list[dict] = []
    tag_re = re.compile(r"\{[^}]*\}")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        raw_text = parts[9]
        text = tag_re.sub("", raw_text)
        entries.append({
            "start": parse_ass_time(parts[1]),
            "end": parse_ass_time(parts[2]),
            "raw": raw_text,
            "text": text,
            "lines": text.split(r"\N"),
        })
    return entries


def validate_caption_layout(entries: list[dict]) -> list[str]:
    failures: list[str] = []
    forbidden_line_start = tuple("、。，．,.!?！？)]}」』】〉》〕）］｝")
    bad_suffix_start = ("ない", "いる", "です", "ます", "でした", "ません", "かもし")

    for index, entry in enumerate(entries, start=1):
        lines = entry["lines"]
        if len(lines) > 2:
            failures.append(f"caption-more-than-2-lines-{index}")
            continue

        if any(len(line) > 18 for line in lines):
            failures.append(f"caption-line-too-long-{index}")

        if len(lines) == 2:
            if min(len(lines[0]), len(lines[1])) <= 3:
                failures.append(f"caption-orphan-line-{index}")
            if lines[1].startswith(forbidden_line_start):
                failures.append(f"caption-kinsoku-start-{index}")
            if lines[1].startswith(bad_suffix_start):
                failures.append(f"caption-broken-expression-{index}")

    return failures


def validate_caption_styling(entries: list[dict]) -> list[str]:
    failures: list[str] = []
    override_re = re.compile(r"\{([^}]*)\}")

    for index, entry in enumerate(entries, start=1):
        raw = str(entry.get("raw") or "")
        if raw.count("{") != raw.count("}"):
            failures.append(f"caption-unbalanced-ass-tags-{index}")
            continue

        for block in override_re.findall(raw):
            if block and "\\" not in block:
                failures.append(f"caption-invalid-ass-tag-{index}")
                break

        if r"\move(" not in raw or r"\fad(" not in raw:
            failures.append(f"caption-missing-entry-animation-{index}")

        if r"\1c&H" in raw:
            if r"\t(0,90," not in raw or r"\t(90,220," not in raw:
                failures.append(f"caption-broken-emphasis-animation-{index}")
            if r"\fscx115\fscy115" not in raw:
                failures.append(f"caption-missing-pop-scale-{index}")

    return failures


def validate_layout_variants(plan: dict) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    allowed = {"center", "left-presenter", "right-presenter", "fullscreen-card"}
    scenes = plan.get("scenes") or []
    used: list[str] = []

    for index, scene in enumerate(scenes, start=1):
        value = str(scene.get("layoutVariant") or "center")
        used.append(value)
        if value not in allowed:
            failures.append(f"invalid-layout-variant-{index}")

    if len(scenes) >= 4 and len(set(used)) <= 1:
        warnings.append("layout-variation-too-low")

    return failures, warnings


def fps_value(rate: str | None) -> float:
    if not rate or rate == "0/0":
        return 0.0
    if "/" in rate:
        a, b = rate.split("/", 1)
        return float(a) / float(b)
    return float(rate)


def main() -> int:
    args = parse_args()
    video = args.video.expanduser().resolve()
    narration = args.narration.expanduser().resolve()
    plan_path = args.scene_plan.expanduser().resolve()
    captions = args.captions.expanduser().resolve()
    script_file = args.script_file.expanduser().resolve()
    report = args.report.expanduser().resolve()

    failures: list[str] = []
    warnings: list[str] = []
    checks: dict = {}

    for name, path in {
        "video": video,
        "narration": narration,
        "scenePlan": plan_path,
        "captions": captions,
        "script": script_file,
    }.items():
        checks[f"{name}Exists"] = path.exists()
        if not path.exists():
            failures.append(f"missing-{name}")

    if failures:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({"passed": False, "failures": failures, "warnings": warnings, "checks": checks}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return 1

    probe = ffprobe(video)
    streams = probe.get("streams", [])
    vstream = next((s for s in streams if s.get("codec_type") == "video"), None)
    astream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not vstream:
        failures.append("missing-video-stream")
    else:
        width = int(vstream.get("width") or 0)
        height = int(vstream.get("height") or 0)
        fps = fps_value(vstream.get("avg_frame_rate"))
        checks["width"] = width
        checks["height"] = height
        checks["fps"] = round(fps, 3)
        if (width, height) != (1080, 1920):
            failures.append("wrong-aspect-or-resolution")
        if not (29.0 <= fps <= 31.0):
            failures.append("wrong-fps")

    if not astream:
        failures.append("missing-audio-stream")

    narration_stats = wav_stats(narration)
    checks["narration"] = narration_stats
    if narration_stats["duration"] <= 0.1 or narration_stats["rms"] < 20:
        failures.append("silent-or-empty-narration")
    if narration_stats["peak"] >= 32767:
        failures.append("narration-clipping")
    elif narration_stats["peak"] >= 30000:
        warnings.append("narration-low-headroom")

    format_duration = float(probe.get("format", {}).get("duration") or 0)
    checks["videoDuration"] = round(format_duration, 3)
    duration_gap = abs(format_duration - narration_stats["duration"])
    checks["durationGap"] = round(duration_gap, 3)
    if duration_gap > 0.35:
        failures.append("audio-video-duration-mismatch")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    approved_script = script_file.read_text(encoding="utf-8").strip()
    checks["scriptPreserved"] = plan.get("script", "").strip() == approved_script
    if not checks["scriptPreserved"]:
        failures.append("approved-script-mutated")
    if plan.get("voice") != "shunri":
        failures.append("wrong-voice")

    layout_failures, layout_warnings = validate_layout_variants(plan)
    failures.extend(layout_failures)
    warnings.extend(layout_warnings)
    checks["captionEmphasis"] = plan.get("captionEmphasis")
    checks["captionEntryAnimation"] = plan.get("captionEntryAnimation")
    checks["motionEngine"] = plan.get("motionEngine")
    checks["layoutEngine"] = plan.get("layoutEngine")
    checks["layoutVariants"] = [
        str(scene.get("layoutVariant") or "center")
        for scene in (plan.get("scenes") or [])
    ]

    windows = caption_windows(captions)
    entries = caption_entries(captions)
    checks["captionCount"] = len(windows)
    checks["captionLayoutEngine"] = "japanese-semantic-v2"
    if not windows:
        failures.append("missing-captions")
    failures.extend(validate_caption_layout(entries))
    failures.extend(validate_caption_styling(entries))
    for i, (start, end) in enumerate(windows):
        if end <= start:
            failures.append(f"invalid-caption-window-{i+1}")
        if i and start < windows[i - 1][1] - 0.03:
            failures.append(f"overlapping-caption-{i+1}")
    if windows and abs(windows[-1][1] - narration_stats["duration"]) > 0.45:
        warnings.append("caption-end-not-close-to-audio-end")

    decode_ok, decode_error = decode_test(video)
    checks["decodePassed"] = decode_ok
    if decode_error:
        checks["decodeError"] = decode_error[:500]
    if not decode_ok:
        failures.append("video-decode-failed")

    file_size = video.stat().st_size
    checks["videoBytes"] = file_size
    if file_size < 100_000:
        failures.append("video-file-too-small")

    payload = {
        "version": 1,
        "passed": len(failures) == 0,
        "failures": sorted(set(failures)),
        "warnings": sorted(set(warnings)),
        "checks": checks,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    print(f"QA: {'PASS' if payload['passed'] else 'FAIL'}")
    print(f"- report: {report}")
    if payload["warnings"]:
        print("- warnings: " + ", ".join(payload["warnings"]))
    if payload["failures"]:
        print("- failures: " + ", ".join(payload["failures"]))

    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
