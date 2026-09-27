#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass

OPENING_PROHIBITED = set("、。，．,.!?！？)]}」』】〉》〕）］｝ーぁぃぅぇぉゃゅょっァィゥェォャュョッ")
CLOSING_PROHIBITED = set("([{「『【〈《〔（［｛")

PROTECTED = (
    "変わっていない",
    "ていない",
    "でいない",
    "ている",
    "でいる",
    "じゃなくて",
    "ではなく",
    "かもしれません",
    "かもしれない",
    "と思って",
    "んですよ",
    "んです",
    "という",
)

PARTICLE_BOUNDARIES = (
    "ではなく、",
    "じゃなくて、",
    "けれど、",
    "けど、",
    "ので、",
    "のに、",
    "から、",
    "なら、",
    "は",
    "が",
    "を",
    "に",
    "で",
    "と",
    "も",
    "へ",
)

KEY_TERMS = (
    "ファーストビュー",
    "仕事が減らない",
    "仕事の流れ",
    "Canva",
    "AI",
    "LP",
    "CTA",
    "CVR",
    "CPA",
)


@dataclass(frozen=True)
class CaptionCue:
    start: float
    end: float
    text: str
    display: str
    highlight: str | None


def _clean(text: str) -> str:
    return re.sub(r"\s+", "", text.replace("{", "（").replace("}", "）")).strip()


def _protected_break(text: str, pos: int) -> bool:
    for phrase in PROTECTED:
        start = 0
        while True:
            idx = text.find(phrase, start)
            if idx < 0:
                break
            if idx < pos < idx + len(phrase):
                return True
            start = idx + 1
    return False


def _boundary_bonus(text: str, pos: int) -> float:
    left = text[:pos]
    right = text[pos:]
    if not left or not right:
        return -999.0
    if right[0] in OPENING_PROHIBITED or left[-1] in CLOSING_PROHIBITED:
        return -999.0
    if _protected_break(text, pos):
        return -999.0

    bonus = 0.0
    if left[-1] in "、，,。！？!?":
        bonus += 7.0

    for token in PARTICLE_BOUNDARIES:
        if left.endswith(token):
            bonus += 4.0 if len(token) > 1 else 2.4
            break

    if right.startswith(("ない", "いる", "です", "ます", "でした", "ません", "かも", "ので", "のに")):
        bonus -= 5.0
    if len(right) <= 3 or len(left) <= 3:
        bonus -= 8.0
    return bonus


def balanced_lines(text: str, max_line_chars: int = 18, min_line_chars: int = 5) -> str:
    clean = _clean(text)
    if len(clean) <= max_line_chars:
        return clean

    candidates: list[tuple[float, int]] = []
    center = len(clean) / 2
    for pos in range(min_line_chars, len(clean) - min_line_chars + 1):
        left_len = pos
        right_len = len(clean) - pos
        if max(left_len, right_len) > max_line_chars:
            continue
        bonus = _boundary_bonus(clean, pos)
        if bonus < -100:
            continue
        balance_penalty = abs(pos - center) * 0.65
        score = bonus - balance_penalty
        candidates.append((score, pos))

    if not candidates:
        # If one two-line caption would be too crowded, the caller should split cues.
        pos = min(max_line_chars, max(min_line_chars, len(clean) // 2))
        while pos > min_line_chars and _protected_break(clean, pos):
            pos -= 1
        return clean[:pos] + r"\N" + clean[pos:]

    _, best = max(candidates)
    return clean[:best] + r"\N" + clean[best:]


def _semantic_split_points(text: str) -> list[int]:
    points: set[int] = set()
    for i, ch in enumerate(text, start=1):
        if ch in "、，,。！？!?":
            points.add(i)
    for token in PARTICLE_BOUNDARIES:
        start = 0
        while True:
            idx = text.find(token, start)
            if idx < 0:
                break
            points.add(idx + len(token))
            start = idx + 1
    return sorted(p for p in points if 0 < p < len(text) and not _protected_break(text, p))


def split_caption_units(text: str, max_unit_chars: int = 30, min_unit_chars: int = 7) -> list[str]:
    clean = _clean(text)
    if len(clean) <= max_unit_chars:
        return [clean]

    points = _semantic_split_points(clean)
    units: list[str] = []
    cursor = 0

    while len(clean) - cursor > max_unit_chars:
        target = cursor + max_unit_chars
        viable = [
            p for p in points
            if cursor + min_unit_chars <= p <= target
        ]
        if viable:
            split = max(viable)
        else:
            split = target
            while split > cursor + min_unit_chars and _protected_break(clean, split):
                split -= 1
        units.append(clean[cursor:split])
        cursor = split

    tail = clean[cursor:]
    if tail:
        if units and len(tail) < 5 and len(units[-1]) + len(tail) <= max_unit_chars + 4:
            units[-1] += tail
        else:
            units.append(tail)
    return units


def choose_highlight(text: str) -> str | None:
    for term in KEY_TERMS:
        if term in text:
            return term

    number = re.search(r"\d+(?:\.\d+)?(?:時間|分|秒|日|%|％|倍|円|万円|件|人)?", text)
    if number:
        return number.group(0)

    acronym = re.search(r"(?<![A-Za-z])[A-Z]{2,6}(?![A-Za-z])", text)
    if acronym:
        return acronym.group(0)

    negative = re.search(r"[^、。！？]{2,10}(?:減らない|増えない|できない|変わらない)", text)
    if negative:
        return negative.group(0)
    return None


def build_caption_cues(
    scenes: list[dict],
    *,
    max_unit_chars: int = 30,
    max_line_chars: int = 18,
) -> list[CaptionCue]:
    cues: list[CaptionCue] = []
    for scene in scenes:
        text = str(scene.get("caption") or scene.get("narration") or "").strip()
        if not text:
            continue

        units = split_caption_units(text, max_unit_chars=max_unit_chars)
        start = float(scene["start"])
        end = float(scene["end"])
        duration = max(0.01, end - start)
        weights = [max(3, len(_clean(unit))) for unit in units]
        total = sum(weights)
        cursor = start

        for index, (unit, weight) in enumerate(zip(units, weights)):
            cue_end = end if index == len(units) - 1 else cursor + duration * weight / total
            display = balanced_lines(unit, max_line_chars=max_line_chars)
            cues.append(
                CaptionCue(
                    start=round(cursor, 3),
                    end=round(cue_end, 3),
                    text=unit,
                    display=display,
                    highlight=choose_highlight(unit),
                )
            )
            cursor = cue_end
    return cues


def ass_text(cue: CaptionCue, default_style: str = "Default") -> str:
    display = cue.display
    if not cue.highlight or cue.highlight not in display.replace(r"\N", ""):
        return display

    # Keep line break positions intact while applying emphasis to the matching phrase.
    plain = display.replace(r"\N", "\u0000")
    marker = cue.highlight
    if marker not in plain:
        return display
    emphasized = plain.replace(
        marker,
        r"{\fs82\b1}" + marker + rf"{{\r{default_style}}}",
        1,
    )
    return emphasized.replace("\u0000", r"\N")
