#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from caption_layout import balanced_lines, build_caption_cues
from reel_poc import camera_motion_filter


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
        },
        {
            "id": "s02",
            "type": "cta",
            "caption": "気づいたら3時間。",
            "start": 2.0,
            "end": 3.0,
            "cameraMotion": "cta-push",
        },
    ]
    cues = build_caption_cues(scenes)
    assert cues
    for cue in cues:
        lines = cue.display.split(r"\N")
        assert len(lines) <= 2
        assert all(len(line) <= 18 for line in lines)

    assert "zoompan=" in camera_motion_filter("punch-in", 1.5)
    assert "zoompan=" in camera_motion_filter("drift-left", 2.0)

    print("reel-self-test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
