#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import wave
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
PROFILE = ROOT / "config" / "reel_profile.json"
MOTION_CONFIG = ROOT / "config" / "motion_bank.json"
IMAGE = "shunri-remotion-renderer:local"
DOCKERFILE = ROOT / "docker" / "remotion-renderer" / "Dockerfile"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Render an existing Shunri scene-plan through the parallel Remotion renderer."
    )
    p.add_argument("--work-dir", type=Path)
    p.add_argument("--audio", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--skip-build", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def newest_work_dir() -> Path:
    plans = [
        p for p in OUTPUTS.glob("**/scene-plan.json")
        if "gemini-voice" not in str(p) and "remotion" not in str(p.parent.name)
    ]
    if not plans:
        raise SystemExit(
            "scene-plan.json が見つかりません。先に make reel FILE=... で1本生成するか "
            "--work-dir を指定してください。"
        )
    return max(plans, key=lambda p: p.stat().st_mtime).parent


def wav_duration(path: Path) -> float | None:
    if path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(path), "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except (wave.Error, OSError, ZeroDivisionError):
        return None


def ensure_docker() -> None:
    if shutil.which("docker") is None:
        raise SystemExit("Docker CLI が見つかりません。")
    probe = subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if probe.returncode != 0:
        raise SystemExit("Docker Desktop を起動してから再実行してください。")


def ensure_image(skip_build: bool) -> None:
    ensure_docker()
    inspect = subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if inspect.returncode == 0:
        return
    if skip_build:
        raise SystemExit(f"Docker image がありません: {IMAGE}")
    print("Remotion renderer Docker image を初回構築します...")
    subprocess.run(
        ["docker", "build", "-f", str(DOCKERFILE), "-t", IMAGE, str(ROOT)],
        check=True,
    )


def motion_bank_source() -> Path:
    cfg = json.loads(MOTION_CONFIG.read_text(encoding="utf-8"))
    production = Path(str(cfg["productionDir"])).expanduser()
    fallback = Path(str(cfg["outputDir"])).expanduser()
    variants = [str(v["id"]) for v in cfg["variants"]]

    if cfg.get("preferProduction") and production.exists():
        if all((production / f"{variant}.mp4").exists() for variant in variants):
            return production
    if fallback.exists():
        return fallback
    raise SystemExit("Motion Bank がありません。先に make motion-bank を実行してください。")


def apply_visual_director(work_dir: Path, plan_path: Path) -> Path:
    directed_path = work_dir / "visual-director-plan.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "visual_director.py"),
            "--scene-plan",
            str(plan_path),
            "--output",
            str(directed_path),
        ],
        check=True,
    )
    return directed_path


def apply_asset_resolver(work_dir: Path, plan_path: Path) -> dict:
    directed_path = apply_visual_director(work_dir, plan_path)
    resolved_path = work_dir / "asset-resolver-plan.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "asset_resolver.py"),
            "--scene-plan",
            str(directed_path),
            "--work-dir",
            str(work_dir),
            "--output",
            str(resolved_path),
        ],
        check=True,
    )
    return json.loads(resolved_path.read_text(encoding="utf-8"))


def prepare_assets(work_dir: Path, plan: dict, audio_override: Path | None) -> tuple[dict, Path]:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    fps = int(profile["output"]["fps"])
    accent = str(profile["captions"]["accentHex"])

    source_audio = (
        audio_override.expanduser().resolve()
        if audio_override
        else (work_dir / "narration.wav").resolve()
    )
    if not source_audio.exists():
        raise SystemExit(f"ナレーション音声がありません: {source_audio}")

    local_audio = work_dir / "remotion-narration.wav"
    if source_audio != local_audio.resolve():
        shutil.copy2(source_audio, local_audio)

    plan_duration = float(plan.get("durationSeconds") or 0)
    audio_duration = wav_duration(local_audio) or plan_duration
    if audio_duration <= 0:
        raise SystemExit("動画尺を決定できません。")

    scale = audio_duration / plan_duration if plan_duration > 0 else 1.0
    bank = motion_bank_source()
    local_bank = work_dir / "motion-bank"
    local_bank.mkdir(parents=True, exist_ok=True)

    scenes = []
    for scene in plan.get("scenes") or []:
        variant = str(scene.get("presenterVariant") or "neutral-talk")
        clip = local_bank / f"{variant}.mp4"
        if not clip.exists():
            source_clip = bank / f"{variant}.mp4"
            if not source_clip.exists():
                raise SystemExit(f"Motion Bank clip がありません: {source_clip}")
            shutil.copy2(source_clip, clip)

        overlay_src = None
        overlay_name = scene.get("overlay")
        if overlay_name:
            candidate = work_dir / "overlays" / str(overlay_name)
            if candidate.exists():
                overlay_src = f"input/overlays/{candidate.name}"

        asset_resolution = scene.get("assetResolution")
        resolved_asset_src = None
        if (
            isinstance(asset_resolution, dict)
            and asset_resolution.get("status") == "resolved"
        ):
            relative_asset = str(asset_resolution.get("relativePath") or "").strip()
            if relative_asset and ".." not in Path(relative_asset).parts:
                resolved_asset_src = f"input/{relative_asset.lstrip('/')}"

        scenes.append(
            {
                "id": str(scene.get("id") or f"s{len(scenes)+1:02d}"),
                "type": str(scene.get("type") or "talk"),
                "caption": str(scene.get("caption") or scene.get("narration") or ""),
                "start": round(float(scene.get("start") or 0) * scale, 4),
                "end": round(float(scene.get("end") or 0) * scale, 4),
                "presenterVariant": variant,
                "presenterSrc": f"input/motion-bank/{variant}.mp4",
                "cameraMotion": str(scene.get("cameraMotion") or "micro-drift"),
                "layoutVariant": str(scene.get("layoutVariant") or "center"),
                "overlaySrc": overlay_src,
                "visualDirection": scene.get("visualDirection"),
                "assetResolution": asset_resolution,
                "resolvedAssetSrc": resolved_asset_src,
            }
        )

    if scenes:
        scenes[-1]["end"] = round(audio_duration, 4)

    props = {
        "durationSeconds": round(audio_duration, 4),
        "fps": fps,
        "accentHex": accent,
        "audioSrc": "input/remotion-narration.wav",
        "scenes": scenes,
    }
    props_path = work_dir / "remotion-props.json"
    props_path.write_text(
        json.dumps(props, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return props, props_path


def main() -> int:
    args = parse_args()
    work_dir = (
        args.work_dir.expanduser().resolve()
        if args.work_dir
        else newest_work_dir().resolve()
    )
    plan_path = work_dir / "scene-plan.json"
    if not plan_path.exists():
        raise SystemExit(f"scene-plan.json がありません: {plan_path}")

    plan = apply_asset_resolver(work_dir, plan_path)
    props, props_path = prepare_assets(work_dir, plan, args.audio)

    output = (
        args.output.expanduser().resolve()
        if args.output
        else work_dir.parent / "shunri-reel-remotion.mp4"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"work-dir: {work_dir}")
    print(f"props: {props_path}")
    print(f"duration: {props['durationSeconds']:.3f}s")
    print(f"scenes: {len(props['scenes'])}")
    print(f"output: {output}")

    if args.dry_run:
        return 0

    ensure_image(args.skip_build)
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{work_dir}:/app/public/input:ro",
        "-v", f"{output.parent}:/output",
        IMAGE,
        "npx", "remotion", "render",
        "src/index.ts",
        "ShunriReel",
        f"/output/{output.name}",
        "--props=/app/public/input/remotion-props.json",
        "--codec=h264",
        "--pixel-format=yuv420p",
        "--crf=20",
        "--concurrency=1",
        "--log=info",
    ]
    subprocess.run(cmd, check=True)
    print()
    print("Remotion Reel rendered.")
    print(f"- video: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
