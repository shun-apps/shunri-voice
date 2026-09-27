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

# Terms that deserve their own high-impact beat instead of only inline color.
# Short acronyms such as AI / LP stay inline by default so the edit does not
# become noisy.
STANDALONE_KEY_TERMS = (
    "ファーストビュー",
    "仕事が減らない",
    "仕事の流れ",
)

DEFAULT_ACCENT_ASS = "&H00007AFF&"  # #FF7A00 in ASS BGR order
ENTRY_START_Y = 1692
ENTRY_END_Y = 1670


@dataclass(frozen=True)
class CaptionCue:
    start: float
    end: float
    text: str
    display: str
    highlight: str | None
    layout_variant: str
    kind: str = "normal"


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


def _punctuation_only(text: str) -> bool:
    return bool(text) and all(ch in "、。，．,.!?！？…・ " for ch in text)


def _standalone_highlight(text: str, marker: str | None) -> bool:
    if not marker:
        return False
    if marker in STANDALONE_KEY_TERMS:
        return True
    # Numbers with their unit are especially effective as isolated visual beats.
    return bool(re.fullmatch(r"\d+(?:\.\d+)?(?:時間|分|秒|日|%|％|倍|円|万円|件|人)?", marker))


def _expand_caption_unit(unit: str) -> list[tuple[str, str, str | None]]:
    clean = _clean(unit)
    marker = choose_highlight(clean)
    if not marker or marker not in clean or not _standalone_highlight(clean, marker):
        return [("normal", clean, marker)]

    before, _, after = clean.partition(marker)
    parts: list[tuple[str, str, str | None]] = []
    if before and not _punctuation_only(before):
        parts.append(("normal", before, choose_highlight(before)))

    # The emphasis beat contains only the key term. Trailing punctuation is
    # intentionally omitted visually; its timing is absorbed into adjacent cues.
    parts.append(("standalone", marker, marker))

    if after and not _punctuation_only(after):
        parts.append(("normal", after, choose_highlight(after)))
    return parts


def build_caption_cues(
    scenes: list[dict],
    *,
    max_unit_chars: int = 18,
    max_line_chars: int = 18,
) -> list[CaptionCue]:
    cues: list[CaptionCue] = []
    for scene in scenes:
        text = str(scene.get("caption") or scene.get("narration") or "").strip()
        if not text:
            continue

        units = split_caption_units(
            text,
            max_unit_chars=max_unit_chars,
            min_unit_chars=4,
        )
        atoms: list[tuple[str, str, str | None]] = []
        for unit in units:
            atoms.extend(_expand_caption_unit(unit))

        start = float(scene["start"])
        end = float(scene["end"])
        duration = max(0.01, end - start)

        # Standalone emphasis receives extra screen time so a short word like
        # "3時間" does not flash too quickly to register.
        weights = [
            max(8, int(len(_clean(text_part)) * 1.8))
            if kind == "standalone"
            else max(3, len(_clean(text_part)))
            for kind, text_part, _ in atoms
        ]
        total = max(1, sum(weights))
        cursor = start

        for index, ((kind, text_part, marker), weight) in enumerate(zip(atoms, weights)):
            cue_end = end if index == len(atoms) - 1 else cursor + duration * weight / total
            display = (
                _clean(text_part)
                if kind == "standalone"
                else balanced_lines(text_part, max_line_chars=max_line_chars)
            )
            cues.append(
                CaptionCue(
                    start=round(cursor, 3),
                    end=round(cue_end, 3),
                    text=text_part,
                    display=display,
                    highlight=marker,
                    layout_variant=str(scene.get("layoutVariant") or "center"),
                    kind=kind,
                )
            )
            cursor = cue_end
    return cues


def ass_entry_prefix(layout_variant: str = "center") -> str:
    if layout_variant == "fullscreen-card":
        return (
            r"{\an2\fs78\move(540,1160,540,1100,0,180)"
            r"\fad(120,80)}"
        )
    return (
        rf"{{\an2\move(540,{ENTRY_START_Y},540,{ENTRY_END_Y},0,180)"
        r"\fad(120,80)}"
    )


def ass_highlight(text: str, accent_ass: str = DEFAULT_ACCENT_ASS) -> str:
    return (
        rf"{{\1c{accent_ass}\b1\fscx100\fscy100"
        r"\t(0,90,\fscx115\fscy115)"
        r"\t(90,220,\fscx100\fscy100)}"
        + text
        + r"{\1c&H00FFFFFF&\b1\fscx100\fscy100}"
    )


def ass_standalone_emphasis(
    text: str,
    layout_variant: str,
    accent_ass: str = DEFAULT_ACCENT_ASS,
) -> str:
    if layout_variant == "fullscreen-card":
        position = r"\an5\move(540,1200,540,1080,0,160)"
        font_size = 126
    else:
        position = r"\an2\move(540,1650,540,1515,0,160)"
        font_size = 122

    return (
        "{"
        + position
        + rf"\fs{font_size}\1c{accent_ass}\3c&H00111111&\bord6\shad1\b1"
        + r"\fscx100\fscy100"
        + r"\t(0,110,\fscx125\fscy125)"
        + r"\t(110,280,\fscx110\fscy110)"
        + r"\fad(70,100)}"
        + text
    )


def ass_text(
    cue: CaptionCue,
    default_style: str = "Default",
    accent_ass: str = DEFAULT_ACCENT_ASS,
) -> str:
    display = cue.display
    if cue.kind == "standalone":
        return ass_standalone_emphasis(
            display,
            cue.layout_variant,
            accent_ass=accent_ass,
        )

    prefix = ass_entry_prefix(cue.layout_variant)

    if not cue.highlight or cue.highlight not in display.replace(r"\N", ""):
        return prefix + display

    # Preserve semantic line breaks while applying one restrained color/pop emphasis.
    plain = display.replace(r"\N", "\u0000")
    marker = cue.highlight
    if marker not in plain:
        return prefix + display

    emphasized = plain.replace(marker, ass_highlight(marker, accent_ass), 1)
    return prefix + emphasized.replace("\u0000", r"\N")
