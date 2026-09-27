#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from caption_layout import ass_text, balanced_lines, build_caption_cues
from qa_reel import caption_entries, validate_caption_layout, validate_caption_styling
from reel_poc import camera_motion_filter, scene_visual_filter


def main() -> int:
    final = "仕事の流れが変わっていないのかもしれません。"
    laid = balanced_lines(final)
    assert laid == r"仕事の流れが\N変わっていないのかもしれません。", laid

    ai_line = balanced_lines("AIを使っているのに、なぜか仕事が減らない。")
    assert ai_line == r"AIを使っているのに、\Nなぜか仕事が減らない。", ai_line

    scenes = [
        {
            "id": "s01",
            "type": "talk",
            "caption": final,
            "start": 0.0,
            "end": 2.0,
            "cameraMotion": "slow-push",
            "layoutVariant": "center",
        },
        {
            "id": "s02",
            "type": "cta",
            "caption": "気づいたら3時間。",
            "start": 2.0,
            "end": 3.0,
            "cameraMotion": "cta-push",
            "layoutVariant": "center",
        },
    ]

    cues = build_caption_cues(scenes)
    assert cues
    for cue in cues:
        lines = cue.display.split(r"\N")
        assert len(lines) <= 2
        assert all(len(line) <= 18 for line in lines)

    emphasized = next(cue for cue in cues if cue.highlight)
    rendered = ass_text(emphasized)
    assert r"\move(" in rendered
    assert r"\fad(" in rendered
    assert r"\1c&H" in rendered
    assert r"\t(0,90,\fscx115\fscy115)" in rendered
    assert r"\t(90,220,\fscx100\fscy100)" in rendered

    assert "zoompan=" in camera_motion_filter("punch-in", 1.5)
    assert "1.12" in camera_motion_filter("punch-in", 1.5)
    assert "overlay=W-w-40" in scene_visual_filter("drift-left", 2.0, "left-presenter", False)
    assert "overlay=40" in scene_visual_filter("drift-right", 2.0, "right-presenter", False)
    full = scene_visual_filter("punch-in", 2.0, "fullscreen-card", True)
    assert "drawbox=" in full
    assert "scale=900:1320" in full

    with tempfile.TemporaryDirectory() as tmp:
        ass = Path(tmp) / "captions.ass"
        ass.write_text(
            "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,"
            + rendered
            + "\n",
            encoding="utf-8",
        )
        entries = caption_entries(ass)
        assert entries
        assert validate_caption_layout(entries) == []
        assert validate_caption_styling(entries) == []

    print("reel-self-test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
