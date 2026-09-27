#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

from caption_timing import align_phrases
from caption_layout import ass_text, build_caption_cues
from reel_audio import generate_audio_tracks

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "reel_profile.json"
MOTION_MANIFEST = ROOT / "config" / "motion_bank.json"
MOTION_PREP = ROOT / "scripts" / "prepare_motion_bank.py"
LIPSYNC = ROOT / "scripts" / "lipsync_scene.py"
QA = ROOT / "scripts" / "qa_reel.py"
AUDIO_HEADROOM = ROOT / "scripts" / "audio_headroom.py"
CLI = ROOT / "scripts" / "shunri_cli.py"
RENDER_IMAGE = "shunri-reel-renderer:local"
RENDER_DOCKERFILE_DIR = ROOT / "docker" / "reel-renderer"
DEFAULT_PRESENTER = (
    Path.home()
    / "shun-x-scheduler"
    / "assets"
    / "instagram"
    / "character"
    / "reference"
    / "canonical_front.jpeg"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Phase-1 Shunri Reel proof-of-concept from an approved script."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", type=Path, help="Approved UTF-8 narration script.")
    group.add_argument("-t", "--text", help="Approved narration text.")
    parser.add_argument(
        "--presenter",
        type=Path,
        default=DEFAULT_PRESENTER,
        help="Presenter image. Defaults to the canonical Shunri front reference in shun-x-scheduler.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "outputs" / "reel-poc" / "shunri-reel-poc.mp4",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip Docker renderer build when the image already exists.",
    )
    parser.add_argument(
        "--static-presenter",
        action="store_true",
        help="Use the old single still presenter instead of the Motion Bank.",
    )
    parser.add_argument(
        "--lipsync-backend",
        choices=["auto", "passthrough", "external"],
        default="auto",
        help="Per-scene lip-sync backend. auto uses SHUNRI_LIPSYNC_COMMAND when configured.",
    )
    parser.add_argument(
        "--overlay-dir",
        type=Path,
        help="Optional directory containing scene overlays named s01.png, s02.jpg, ...",
    )
    parser.add_argument(
        "--bgm",
        type=Path,
        help="Optional BGM file. Narration remains master and BGM is auto-ducked.",
    )
    parser.add_argument(
        "--no-auto-audio",
        action="store_true",
        help="Disable the built-in original ambient BGM / sparse SFX bed.",
    )
    parser.add_argument(
        "--skip-qa",
        action="store_true",
        help="Skip deterministic output QA.",
    )
    return parser.parse_args()


def load_script(args: argparse.Namespace) -> str:
    if args.file:
        path = args.file.expanduser().resolve()
        if not path.exists():
            raise SystemExit(f"台本ファイルが見つかりません: {path}")
        text = path.read_text(encoding="utf-8").strip()
    else:
        text = (args.text or "").strip()
    if not text:
        raise SystemExit("台本が空です。")
    return text


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        rate = audio.getframerate()
        frames = audio.getnframes()
    return frames / rate if rate else 0.0


def split_long_phrase(text: str, max_chars: int = 24) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    pieces = [x.strip() for x in re.split(r"(?<=[、，,])", text) if x.strip()]
    if len(pieces) == 1:
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) > max_chars:
            chunks.append(current)
            current = piece
        else:
            current += piece
    if current:
        chunks.append(current)
    return chunks


def split_script(text: str) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text)
    rough = [
        p.strip()
        for p in re.split(r"(?<=[。！？!?])|\n+", normalized)
        if p.strip()
    ]
    phrases: list[str] = []
    for item in rough:
        phrases.extend(split_long_phrase(item))
    return phrases


def ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def wrap_caption(text: str, max_chars: int = 16) -> str:
    clean = text.replace("{", "（").replace("}", "）").strip()
    if len(clean) <= max_chars:
        return clean
    if len(clean) <= max_chars * 2:
        split = len(clean) // 2
        candidates = [
            i for i, ch in enumerate(clean)
            if ch in "、，,。！？!?" and 5 <= i <= len(clean) - 5
        ]
        if candidates:
            split = min(candidates, key=lambda i: abs(i - len(clean) / 2)) + 1
        return clean[:split] + r"\N" + clean[split:]
    return clean[:max_chars] + r"\N" + clean[max_chars : max_chars * 2]


def motion_variant_ids() -> list[str]:
    data = json.loads(MOTION_MANIFEST.read_text(encoding="utf-8"))
    return [str(item["id"]) for item in data.get("variants", [])]


def bank_is_complete(path: Path, variants: list[str]) -> bool:
    return path.exists() and all((path / f"{variant}.mp4").exists() for variant in variants)


def motion_bank_dir() -> Path:
    data = json.loads(MOTION_MANIFEST.read_text(encoding="utf-8"))
    variants = [str(item["id"]) for item in data.get("variants", [])]

    production_raw = data.get("productionDir")
    if data.get("preferProduction", True) and production_raw:
        production = Path(str(production_raw)).expanduser()
        if bank_is_complete(production, variants):
            print(f"Motion Bank: production ({production})")
            return production

    generated = Path(data["outputDir"]).expanduser()
    return generated


def assign_motion_variants(timeline: list[dict]) -> list[dict]:
    variants = motion_variant_ids()
    regular = [v for v in variants if v != "cta-forward"]
    if not regular:
        regular = ["neutral-talk"]

    camera_cycle = [
        "slow-push",
        "drift-left",
        "punch-in",
        "drift-right",
        "slow-push",
        "micro-drift",
    ]

    for index, scene in enumerate(timeline):
        if scene.get("type") == "cta" and "cta-forward" in variants:
            scene["presenterVariant"] = "cta-forward"
            scene["cameraMotion"] = "cta-push"
        else:
            scene["presenterVariant"] = regular[index % len(regular)]
            scene["cameraMotion"] = camera_cycle[index % len(camera_cycle)]
    return timeline


def ensure_motion_bank() -> Path:
    bank = motion_bank_dir()
    variants = motion_variant_ids()
    missing = [v for v in variants if not (bank / f"{v}.mp4").exists()]
    if missing:
        print("瞬理 Motion Bank が未準備です。初回生成します...")
        subprocess.run([sys.executable, str(MOTION_PREP)], cwd=ROOT, check=True)
        missing = [v for v in variants if not (bank / f"{v}.mp4").exists()]
        if missing:
            raise SystemExit("Motion Bank生成後も不足しています: " + ", ".join(missing))
    return bank


def build_timeline(phrases: list[str], duration: float, narration_path: Path) -> list[dict]:
    if not phrases:
        return []

    aligned = align_phrases(narration_path, phrases, duration)
    timeline: list[dict] = []
    for index, (phrase, (start, end)) in enumerate(zip(phrases, aligned), start=1):
        timeline.append(
            {
                "id": f"s{index:02d}",
                "type": "cta" if index == len(phrases) else "talk",
                "narration": phrase,
                "caption": phrase,
                "start": round(start, 3),
                "end": round(end, 3),
                "motion": "subtle-push-in" if index % 3 == 0 else "none",
                "captionAlignment": "speech-energy-pauses-v1",
            }
        )
    return assign_motion_variants(timeline)


def prepare_overlays(job_dir: Path, timeline: list[dict], overlay_dir: Path | None) -> None:
    if overlay_dir is None:
        return
    source_dir = overlay_dir.expanduser().resolve()
    if not source_dir.exists():
        raise SystemExit(f"overlay directory がありません: {source_dir}")

    dest_dir = job_dir / "overlays"
    dest_dir.mkdir(parents=True, exist_ok=True)
    extensions = [".png", ".jpg", ".jpeg", ".webp"]

    for scene in timeline:
        scene_id = str(scene["id"])
        source = next((source_dir / f"{scene_id}{ext}" for ext in extensions if (source_dir / f"{scene_id}{ext}").exists()), None)
        if source is None:
            continue
        destination = dest_dir / source.name
        shutil.copy2(source, destination)
        scene["overlay"] = destination.name
        if scene.get("type") == "talk":
            scene["type"] = "talk_overlay"


def prepare_bgm(job_dir: Path, bgm: Path | None) -> Path | None:
    if bgm is None:
        return None
    source = bgm.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"BGM が見つかりません: {source}")
    destination = job_dir / ("bgm" + source.suffix.lower())
    shutil.copy2(source, destination)
    return destination


def write_plan(path: Path, script: str, duration: float, timeline: list[dict]) -> None:
    data = {
        "version": 1,
        "format": "shunri-reel-v1",
        "scriptApproved": True,
        "voice": "shunri",
        "durationSeconds": round(duration, 3),
        "script": script,
        "captionEngine": "japanese-semantic-v2",
        "motionEngine": "editorial-camera-v1",
        "audioDesign": "auto-editorial-v1",
        "scenes": timeline,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_ass(path: Path, timeline: list[dict], width: int, height: int) -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Noto Sans CJK JP,66,&H00FFFFFF,&H000000FF,&H00111111,&H7A000000,-1,0,0,0,100,100,0,0,1,5,1,2,80,80,250,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    lines = [header]
    cues = build_caption_cues(timeline, max_unit_chars=30, max_line_chars=18)
    for cue in cues:
        start = ass_time(float(cue.start))
        end = ass_time(float(cue.end))
        caption = ass_text(cue)
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{caption}\n")
    path.write_text("".join(lines), encoding="utf-8")


def docker_daemon_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def ensure_docker_daemon(timeout_seconds: int = 120) -> None:
    if shutil.which("docker") is None:
        raise SystemExit("Docker CLI が見つかりません。Docker Desktop のインストールを確認してください。")
    if docker_daemon_ready():
        return
    if platform.system() == "Darwin":
        print("Docker Desktop が停止しています。自動起動します...")
        opened = subprocess.run(
            ["open", "-a", "Docker"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if opened.returncode != 0:
            raise SystemExit("Docker Desktop を自動起動できませんでした。Applications から Docker を起動してください。")
        waited = 0
        while waited < timeout_seconds:
            if docker_daemon_ready():
                print("Docker Desktop の起動を確認しました。")
                return
            time.sleep(2)
            waited += 2
        raise SystemExit(
            f"Docker Desktop が {timeout_seconds} 秒以内に起動しませんでした。"
            " Docker Desktop の画面を確認して再実行してください。"
        )
    raise SystemExit("Docker daemon が停止しています。Docker を起動してから再実行してください。")


def ensure_renderer_image(skip_build: bool) -> None:
    ensure_docker_daemon()
    if skip_build:
        return
    inspect = subprocess.run(
        ["docker", "image", "inspect", RENDER_IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if inspect.returncode == 0:
        return
    print("Reel renderer Docker image を初回構築します...")
    subprocess.run(
        ["docker", "build", "-t", RENDER_IMAGE, str(RENDER_DOCKERFILE_DIR)],
        check=True,
    )


def render_static(job_dir: Path, duration: float, output_name: str) -> None:
    filter_graph = (
        "[0:v]split=2[bg0][fg0];"
        "[bg0]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=30:10[bg];"
        "[fg0]scale=900:1450:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2-80,"
        "subtitles=/work/captions.ass:fontsdir=/usr/share/fonts/opentype/noto[outv]"
    )

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{job_dir.resolve()}:/work",
        RENDER_IMAGE,
        "-y",
        "-loop", "1",
        "-framerate", "30",
        "-i", "/work/presenter.jpg",
        "-i", "/work/narration.wav",
        "-filter_complex", filter_graph,
        "-map", "[outv]",
        "-map", "1:a:0",
        "-t", f"{duration:.3f}",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        f"/work/{output_name}",
    ]
    subprocess.run(cmd, check=True)


def copy_motion_bank(job_dir: Path, timeline: list[dict]) -> Path:
    source_dir = ensure_motion_bank()
    dest = job_dir / "motion-bank"
    dest.mkdir(parents=True, exist_ok=True)
    needed = sorted({str(scene["presenterVariant"]) for scene in timeline})
    for variant in needed:
        source = source_dir / f"{variant}.mp4"
        if not source.exists():
            raise SystemExit(f"Motion Bank clip がありません: {source}")
        shutil.copy2(source, dest / source.name)
    return dest


def extract_scene_audio(job_dir: Path, start: float, duration: float, output_name: str) -> Path:
    audio_dir = job_dir / "scene-audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    output = audio_dir / output_name
    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{job_dir.resolve()}:/work",
            RENDER_IMAGE,
            "-y",
            "-ss", f"{start:.3f}",
            "-t", f"{duration:.3f}",
            "-i", "/work/narration.wav",
            "-ac", "1",
            "-ar", "48000",
            "-c:a", "pcm_s16le",
            f"/work/scene-audio/{output_name}",
        ],
        check=True,
    )
    return output


def camera_motion_filter(name: str, scene_duration: float) -> str:
    frames = max(1, int(scene_duration * 30))
    center_x = "iw/2-(iw/zoom/2)"
    center_y = "ih/2-(ih/zoom/2)"

    if name == "punch-in":
        zoom = "if(lt(on,12),1+0.004*on,1.048)"
        x = center_x
        y = center_y
    elif name == "drift-left":
        zoom = "1.035"
        x = f"(iw-iw/zoom)*(0.72-0.44*on/{frames})"
        y = center_y
    elif name == "drift-right":
        zoom = "1.035"
        x = f"(iw-iw/zoom)*(0.28+0.44*on/{frames})"
        y = center_y
    elif name == "cta-push":
        zoom = f"1+0.065*on/{frames}"
        x = center_x
        y = center_y
    elif name == "slow-push":
        zoom = f"1+0.045*on/{frames}"
        x = center_x
        y = center_y
    else:
        zoom = "1.025"
        x = f"(iw-iw/zoom)*(0.48+0.04*sin(on/{max(1, frames // 3)}))"
        y = center_y

    return (
        "zoompan="
        f"z='{zoom}':x='{x}':y='{y}':"
        "d=1:s=1080x1920:fps=30"
    )


def render_scene_visual(
    job_dir: Path,
    synced_name: str,
    final_name: str,
    scene_duration: float,
    overlay_name: str | None,
    camera_motion: str,
) -> None:
    base = [
        "docker", "run", "--rm",
        "-v", f"{job_dir.resolve()}:/work",
        RENDER_IMAGE,
        "-y",
        "-i", f"/work/segments-synced/{synced_name}",
    ]
    motion = camera_motion_filter(camera_motion, scene_duration)

    if overlay_name:
        out_start = max(0.10, scene_duration - 0.24)
        filter_graph = (
            f"[0:v]{motion}[base];"
            "[1:v]scale=840:620:force_original_aspect_ratio=decrease,"
            "pad=864:644:12:12:color=white,format=rgba,"
            "fade=t=in:st=0:d=0.18:alpha=1,"
            f"fade=t=out:st={out_start:.3f}:d=0.22:alpha=1[ov];"
            "[base][ov]overlay=x=(W-w)/2:"
            "y='if(lt(t,0.35),-h+(120+h)*(t/0.35),120)'"
            ":shortest=1[outv]"
        )
        cmd = base + [
            "-loop", "1",
            "-i", f"/work/overlays/{overlay_name}",
            "-filter_complex", filter_graph,
            "-map", "[outv]",
            "-t", f"{scene_duration:.3f}",
            "-an",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            f"/work/segments/{final_name}",
        ]
    else:
        cmd = base + [
            "-vf", motion,
            "-t", f"{scene_duration:.3f}",
            "-an",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            f"/work/segments/{final_name}",
        ]

    subprocess.run(cmd, check=True)


def render_motion_track(job_dir: Path, timeline: list[dict], lipsync_backend: str) -> Path:
    segments_dir = job_dir / "segments"
    raw_dir = job_dir / "segments-raw"
    synced_dir = job_dir / "segments-synced"
    segments_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    synced_dir.mkdir(parents=True, exist_ok=True)
    concat_lines: list[str] = []

    for index, scene in enumerate(timeline, start=1):
        variant = str(scene["presenterVariant"])
        scene_start = float(scene["start"])
        scene_duration = max(0.25, float(scene["end"]) - scene_start)
        raw_name = f"raw-{index:02d}.mp4"
        synced_name = f"synced-{index:02d}.mp4"
        final_name = f"segment-{index:02d}.mp4"

        subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{job_dir.resolve()}:/work",
                RENDER_IMAGE,
                "-y",
                "-stream_loop", "-1",
                "-i", f"/work/motion-bank/{variant}.mp4",
                "-t", f"{scene_duration:.3f}",
                "-an",
                "-r", "30",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                f"/work/segments-raw/{raw_name}",
            ],
            check=True,
        )

        scene_audio = extract_scene_audio(
            job_dir,
            scene_start,
            scene_duration,
            f"scene-{index:02d}.wav",
        )

        subprocess.run(
            [
                sys.executable,
                str(LIPSYNC),
                "--video", str(raw_dir / raw_name),
                "--audio", str(scene_audio),
                "--output", str(synced_dir / synced_name),
                "--backend", lipsync_backend,
            ],
            cwd=ROOT,
            check=True,
        )

        render_scene_visual(
            job_dir,
            synced_name,
            final_name,
            scene_duration,
            str(scene.get("overlay")) if scene.get("overlay") else None,
            str(scene.get("cameraMotion") or "micro-drift"),
        )
        concat_lines.append(f"file '{final_name}'")

    concat_file = segments_dir / "concat.txt"
    concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    presenter_track = job_dir / "presenter-track.mp4"

    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{job_dir.resolve()}:/work",
            RENDER_IMAGE,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", "/work/segments/concat.txt",
            "-c", "copy",
            "/work/presenter-track.mp4",
        ],
        check=True,
    )
    return presenter_track

def render_motion(
    job_dir: Path,
    duration: float,
    output_name: str,
    timeline: list[dict],
    lipsync_backend: str,
    bgm_path: Path | None,
    sfx_path: Path | None,
) -> None:
    copy_motion_bank(job_dir, timeline)
    render_motion_track(job_dir, timeline, lipsync_backend)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{job_dir.resolve()}:/work",
        RENDER_IMAGE,
        "-y",
        "-i", "/work/presenter-track.mp4",
        "-i", "/work/narration.wav",
    ]

    bgm_index: int | None = None
    sfx_index: int | None = None
    next_index = 2

    if bgm_path is not None:
        bgm_index = next_index
        next_index += 1
        cmd += ["-stream_loop", "-1", "-i", f"/work/{bgm_path.name}"]

    if sfx_path is not None:
        sfx_index = next_index
        cmd += ["-i", f"/work/{sfx_path.name}"]

    if bgm_index is not None or sfx_index is not None:
        filters = [
            "[0:v]subtitles=/work/captions.ass:fontsdir=/usr/share/fonts/opentype/noto[vout]"
        ]
        audio_inputs = ["[1:a]"]

        if bgm_index is not None:
            filters.append(
                f"[{bgm_index}:a]volume=0.85[bgm];"
                "[bgm][1:a]sidechaincompress="
                "threshold=0.018:ratio=9:attack=20:release=380[ducked]"
            )
            audio_inputs.append("[ducked]")

        if sfx_index is not None:
            filters.append(f"[{sfx_index}:a]volume=0.48[sfx]")
            audio_inputs.append("[sfx]")

        filters.append(
            "".join(audio_inputs)
            + f"amix=inputs={len(audio_inputs)}:normalize=0,"
            "alimiter=limit=0.90[aout]"
        )
        cmd += [
            "-filter_complex", ";".join(filters),
            "-map", "[vout]",
            "-map", "[aout]",
        ]
    else:
        cmd += [
            "-vf", "subtitles=/work/captions.ass:fontsdir=/usr/share/fonts/opentype/noto",
            "-map", "0:v:0",
            "-map", "1:a:0",
        ]

    cmd += [
        "-t", f"{duration:.3f}",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        f"/work/{output_name}",
    ]
    subprocess.run(cmd, check=True)

def main() -> int:
    args = parse_args()
    script = load_script(args)

    presenter = args.presenter.expanduser().resolve()
    if not presenter.exists():
        raise SystemExit(
            "瞬理の正準人物画像が見つかりません。\n"
            f"期待パス: {presenter}\n"
            "先に ~/shun-x-scheduler を git pull するか、--presenter で画像を指定してください。"
        )

    profile = json.loads(CONFIG.read_text(encoding="utf-8"))
    width = int(profile["output"]["width"])
    height = int(profile["output"]["height"])

    output = args.output.expanduser().resolve()
    job_dir = output.parent / ".poc-work"
    job_dir.mkdir(parents=True, exist_ok=True)

    script_path = job_dir / "script.txt"
    narration_path = job_dir / "narration.wav"
    plan_path = job_dir / "scene-plan.json"
    ass_path = job_dir / "captions.ass"
    presenter_copy = job_dir / "presenter.jpg"

    script_path.write_text(script + "\n", encoding="utf-8")
    shutil.copy2(presenter, presenter_copy)

    print("[1/4] 瞬理の正式声でナレーション生成")
    subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--file",
            str(script_path),
            "--output",
            str(narration_path),
        ],
        cwd=ROOT,
        check=True,
    )

    subprocess.run(
        [sys.executable, str(AUDIO_HEADROOM), str(narration_path)],
        cwd=ROOT,
        check=True,
    )

    duration = wav_duration(narration_path)
    if duration <= 0:
        raise SystemExit("ナレーション音声の長さを取得できませんでした。")

    print("[2/4] 台本をシーン / 字幕へ分割")
    phrases = split_script(script)
    timeline = build_timeline(phrases, duration, narration_path)
    prepare_overlays(job_dir, timeline, args.overlay_dir)
    external_bgm = prepare_bgm(job_dir, args.bgm)
    auto_bgm: Path | None = None
    auto_sfx: Path | None = None
    if not args.no_auto_audio:
        auto_bgm, auto_sfx = generate_audio_tracks(job_dir, duration, timeline)
    bgm_path = external_bgm or auto_bgm
    sfx_path = auto_sfx
    write_plan(plan_path, script, duration, timeline)
    write_ass(ass_path, timeline, width, height)

    print("[3/4] Reel renderer 準備")
    ensure_renderer_image(args.skip_build)

    print("[4/4] 1080x1920 MP4 をレンダリング")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = job_dir / output.name
    if args.static_presenter:
        render_static(job_dir, duration, output.name)
    else:
        print("Motion Bank を使ってPresenterカットを自動構成します。")
        render_motion(
            job_dir,
            duration,
            output.name,
            timeline,
            args.lipsync_backend,
            bgm_path,
            sfx_path,
        )
    shutil.copy2(temp_output, output)

    qa_report = job_dir / "qa-report.json"
    if not args.skip_qa:
        print("[QA] Reel自動検査")
        qa = subprocess.run(
            [
                sys.executable,
                str(QA),
                "--video", str(output),
                "--narration", str(narration_path),
                "--scene-plan", str(plan_path),
                "--captions", str(ass_path),
                "--script-file", str(script_path),
                "--report", str(qa_report),
            ],
            cwd=ROOT,
            check=False,
        )
        if qa.returncode != 0:
            raise SystemExit(f"Reel QAで不合格になりました: {qa_report}")

    print()
    print("Shunri Reel を生成しました。")
    print(f"- video: {output}")
    print(f"- narration: {narration_path}")
    print(f"- scene plan: {plan_path}")
    print(f"- captions: {ass_path}")
    if not args.skip_qa:
        print(f"- QA: {qa_report}")
    if args.overlay_dir:
        print(f"- overlays: {args.overlay_dir.expanduser().resolve()}")
    if args.bgm:
        print(f"- BGM: {args.bgm.expanduser().resolve()}")
    print()
    if args.static_presenter:
        print("注: --static-presenter のため旧静止画モードです。")
    else:
        print("Phase-6: semantic captions / editorial motion / animated overlays / BGM+SFX / QA が有効です。")
        if args.lipsync_backend == "auto":
            print("lip-sync: SHUNRI_LIPSYNC_COMMAND があればexternal、なければpassthroughです。")
        else:
            print(f"lip-sync backend: {args.lipsync_backend}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
