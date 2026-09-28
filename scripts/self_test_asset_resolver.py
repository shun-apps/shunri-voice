#!/usr/bin/env python3
from pathlib import Path
from tempfile import TemporaryDirectory

from asset_resolver import resolve

CFG = {
    "version": 1,
    "imageExtensions": [".png", ".jpg", ".jpeg", ".webp"],
    "videoExtensions": [".mp4", ".mov", ".webm"],
    "requiredKindsByVisualType": {
        "screenshot": ["image"],
        "b-roll": ["image", "video"],
    },
    "searchDirsByVisualType": {
        "screenshot": ["overlays", "screenshots", "assets"],
        "b-roll": ["broll", "assets", "overlays"],
    },
    "defaultSearchDirs": ["overlays", "assets"],
}

with TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "overlays").mkdir()
    (root / "broll").mkdir()
    (root / "overlays" / "s01.png").write_bytes(b"png")
    (root / "broll" / "s02.mp4").write_bytes(b"mp4")

    plan = {
        "durationSeconds": 8,
        "scenes": [
            {
                "id": "s01",
                "caption": "画面を見てください",
                "overlay": "s01.png",
                "visualDirection": {"visualType": "screenshot"},
            },
            {
                "id": "s02",
                "caption": "現場のイメージです",
                "visualDirection": {"visualType": "b-roll"},
            },
            {
                "id": "s03",
                "caption": "別の画面です",
                "visualDirection": {"visualType": "screenshot"},
            },
            {
                "id": "s04",
                "caption": "通常説明",
                "visualDirection": {"visualType": "presenter"},
            },
            {
                "id": "s05",
                "caption": "明示素材が欠けている",
                "overlay": "s05.png",
                "visualDirection": {"visualType": "presenter"},
            },
        ],
    }

    out = resolve(plan, root, CFG)
    scenes = out["scenes"]

    assert scenes[0]["assetResolution"]["status"] == "resolved"
    assert scenes[0]["assetResolution"]["kind"] == "image"
    assert scenes[0]["assetResolution"]["relativePath"] == "overlays/s01.png"

    assert scenes[1]["assetResolution"]["status"] == "resolved"
    assert scenes[1]["assetResolution"]["kind"] == "video"
    assert scenes[1]["assetResolution"]["relativePath"] == "broll/s02.mp4"

    assert scenes[2]["assetResolution"]["status"] == "missing"
    assert scenes[2]["assetResolution"]["requiredKinds"] == ["image"]

    assert scenes[3]["assetResolution"]["status"] == "not-required"
    assert scenes[4]["assetResolution"]["status"] == "missing"
    assert scenes[4]["assetResolution"]["reason"] == "explicit-overlay-not-found"
    assert out["assetResolver"]["counts"] == {
        "resolved": 2,
        "missing": 2,
        "not-required": 1,
    }

print("asset-resolver-self-test: OK")
