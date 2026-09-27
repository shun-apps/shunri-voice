#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "gemini_voice_candidates.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "gemini-voice-candidates"
API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
_FORCE_CURL = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create and audition Shunri Voice Design candidates with Gemini 3.8 Flash TTS."
    )
    parser.add_argument("--count", type=int, default=5, choices=range(1, 6))
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force-new", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_config(path: Path) -> dict:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise SystemExit(f"config が見つかりません: {resolved}")
    return json.loads(resolved.read_text(encoding="utf-8"))


def _curl_request_json(url: str, payload: dict, api_key: str) -> dict:
    curl = shutil.which("curl")
    if not curl:
        raise SystemExit(
            "PythonのTLS証明書検証に失敗し、curl fallbackも利用できません。"
        )

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    with tempfile.TemporaryDirectory(prefix="shunri-gemini-") as tmp:
        tmp_path = Path(tmp)
        headers_path = tmp_path / "headers.txt"
        payload_path = tmp_path / "payload.json"
        headers_path.write_text(
            "x-goog-api-key: " + api_key + "\n"
            "Content-Type: application/json\n",
            encoding="utf-8",
        )
        os.chmod(headers_path, 0o600)
        payload_path.write_bytes(body)

        proc = subprocess.run(
            [
                curl,
                "--fail-with-body",
                "--silent",
                "--show-error",
                "--max-time",
                "180",
                "-X",
                "POST",
                url,
                "-H",
                f"@{headers_path}",
                "--data-binary",
                f"@{payload_path}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            detail = (proc.stdout or proc.stderr or "").strip()
            raise SystemExit(f"Gemini API curl error: {detail}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise SystemExit(
                "Gemini API response was not valid JSON: "
                + proc.stdout[:500]
            ) from exc


def request_json(path: str, payload: dict, api_key: str) -> dict:
    global _FORCE_CURL
    url = API_ROOT + path
    if _FORCE_CURL:
        return _curl_request_json(url, payload, api_key)
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Gemini API error {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        ssl_failure = isinstance(reason, ssl.SSLCertVerificationError) or (
            "CERTIFICATE_VERIFY_FAILED" in str(exc)
        )
        if ssl_failure:
            _FORCE_CURL = True
            print(
                "PythonのCA証明書チェーンで検証できなかったため、"
                "TLS検証を無効化せずmacOS curlへ切り替えます。"
                " 以降のGemini API呼び出しもcurlを使用します。"
            )
            return _curl_request_json(url, payload, api_key)
        raise SystemExit(f"Gemini API connection error: {exc}") from exc


def maybe_audio_data(obj: dict) -> str | None:
    audio = obj.get("sample_audio") or obj.get("sampleAudio") or {}
    data = audio.get("data") if isinstance(audio, dict) else None
    return str(data) if data else None


def interaction_audio_data(obj: dict) -> str | None:
    # Current REST response exposes model audio under steps[].content[].
    found: str | None = None
    for step in obj.get("steps") or []:
        if not isinstance(step, dict) or step.get("type") != "model_output":
            continue
        for item in step.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "audio" and item.get("data"):
                found = str(item["data"])

    # Keep a small compatibility fallback for SDK-shaped JSON payloads.
    if found:
        return found
    output_audio = obj.get("output_audio") or obj.get("outputAudio") or {}
    if isinstance(output_audio, dict) and output_audio.get("data"):
        return str(output_audio["data"])
    return None


def create_voice(candidate: dict, config: dict, api_key: str) -> dict:
    payload = {
        "store": True,
        "voice": {
            "model": config["model"],
            "type": "prompted",
            "display_name": candidate["displayName"],
            "gender": config["gender"],
            "language_code": config["languageCode"],
            "prompted": {"input": candidate["prompt"]},
        },
    }
    return request_json("/voices", payload, api_key)


def synthesize(voice_id: str, config: dict, api_key: str) -> dict:
    payload = {
        "model": config["model"],
        "input": [{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": config["auditionText"],
                "annotations": [{
                    "type": "speech_metadata",
                    "style": config["auditionStyle"],
                }],
            }],
        }],
        "response_format": {"type": "audio"},
        "generation_config": {
            "speech_config": [{"voice": voice_id}],
        },
    }
    return request_json("/interactions", payload, api_key)


def write_audio(path: Path, encoded: str) -> None:
    path.write_bytes(base64.b64decode(encoded))


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    candidates = list(config["candidates"])[: args.count]

    if args.dry_run:
        print(f"model: {config['model']}")
        print(f"language: {config['languageCode']}")
        for index, candidate in enumerate(candidates, start=1):
            print(f"{index}. {candidate['displayName']} — {candidate['prompt']}")
        return 0

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "GEMINI_API_KEY が未設定です。APIキーはChatGPTやGitHubへ貼らず、"
            "MacのTerminalで export GEMINI_API_KEY='...' と設定してください。"
        )

    output_dir = args.output_dir.expanduser().resolve()
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists() and not args.force_new:
        raise SystemExit(
            f"既存候補があります: {manifest_path}\n"
            "新しいvoice_idを追加作成する場合だけ --force-new を付けてください。"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for index, candidate in enumerate(candidates, start=1):
        slug = str(candidate["id"])
        print(f"[{index}/{len(candidates)}] create: {candidate['displayName']}")
        created = create_voice(candidate, config, api_key)
        voice_id = str(created.get("id") or "")
        if not voice_id:
            raise SystemExit("Voice Design response に voice id がありません。")

        preview = maybe_audio_data(created)
        preview_path = output_dir / f"{index:02d}-{slug}-preview.wav"
        if preview:
            write_audio(preview_path, preview)

        print(f"  voice_id: {voice_id}")
        print("  synthesize audition script...")
        generated = synthesize(voice_id, config, api_key)
        audio = interaction_audio_data(generated)
        if not audio:
            raise SystemExit("TTS response に audio data がありません。")

        audition_path = output_dir / f"{index:02d}-{slug}-audition.wav"
        write_audio(audition_path, audio)

        results.append({
            "id": slug,
            "displayName": candidate["displayName"],
            "voiceId": voice_id,
            "prompt": candidate["prompt"],
            "preview": str(preview_path) if preview else None,
            "audition": str(audition_path),
        })

    manifest = {
        "version": 1,
        "model": config["model"],
        "languageCode": config["languageCode"],
        "auditionText": config["auditionText"],
        "auditionStyle": config["auditionStyle"],
        "candidates": results,
        "note": "Designed voice IDs are project-scoped and time-limited. Keep the design prompts as the canonical source of truth.",
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print()
    print("Gemini Shunri voice candidates created.")
    print(f"- dir: {output_dir}")
    print(f"- manifest: {manifest_path}")
    print()
    print("Mac audition:")
    for item in results:
        print(f"  afplay {item['audition']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
