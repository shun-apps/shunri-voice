#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    package = json.loads((ROOT / "remotion" / "package.json").read_text(encoding="utf-8"))
    deps = package["dependencies"]
    assert deps["remotion"] == "4.0.529"
    assert deps["@remotion/cli"] == "4.0.529"
    assert deps["@remotion/media"] == "4.0.529"
    assert not deps["remotion"].startswith("^")

    dockerfile = (ROOT / "docker" / "remotion-renderer" / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM node:22-bookworm-slim" in dockerfile
    assert "fonts-noto-cjk" in dockerfile
    assert "npx remotion browser ensure" in dockerfile

    reel = (ROOT / "remotion" / "src" / "ShunriReel.tsx").read_text(encoding="utf-8")
    assert "CaptionBeat" in reel
    assert "PresenterScene" in reel
    assert "Audio" in reel
    assert "hideDefaultCaptions" in reel
    assert "durationInFrames={durationInFrames}" in reel

    directed = (ROOT / "remotion" / "src" / "components" / "DirectedVisual.tsx").read_text(encoding="utf-8")
    assert "ScreenshotVisual" in directed
    assert "BrollVisual" in directed
    assert "resolvedAssetSrc" in directed

    screenshot = (ROOT / "remotion" / "src" / "components" / "ScreenshotVisual.tsx").read_text(encoding="utf-8")
    assert "scene.resolvedAssetSrc" in screenshot
    assert "objectFit=\"contain\"" in screenshot

    broll = (ROOT / "remotion" / "src" / "components" / "BrollVisual.tsx").read_text(encoding="utf-8")
    assert "scene.resolvedAssetSrc" in broll
    assert "objectFit=\"cover\"" in broll

    print("remotion-self-test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
