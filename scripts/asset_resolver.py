#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "asset_resolver.json"


def classify_kind(path: Path, cfg: dict) -> str | None:
    suffix = path.suffix.lower()
    if suffix in cfg["imageExtensions"]:
        return "image"
    if suffix in cfg["videoExtensions"]:
        return "video"
    return None


def relative_inside(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def explicit_overlay(scene: dict, work_dir: Path, cfg: dict) -> dict | None:
    value = str(scene.get("overlay") or "").strip()
    if not value:
        return None

    raw = Path(value)
    if raw.is_absolute():
        return {
            "status": "missing",
            "reason": "blocked-absolute-overlay-path",
        }

    candidates = []
    if len(raw.parts) == 1:
        candidates.append(work_dir / "overlays" / raw)
    candidates.append(work_dir / raw)

    for candidate in candidates:
        rel = relative_inside(candidate, work_dir)
        if rel is None or not candidate.is_file():
            continue
        kind = classify_kind(candidate, cfg)
        if kind is None:
            continue
        return {
            "status": "resolved",
            "kind": kind,
            "relativePath": rel,
            "source": "explicit-overlay",
            "reason": "scene.overlay",
        }

    return {
        "status": "missing",
        "reason": "explicit-overlay-not-found",
    }


def convention_asset(
    scene_id: str,
    visual_type: str,
    work_dir: Path,
    cfg: dict,
    required_kinds: list[str],
) -> dict | None:
    dirs = cfg.get("searchDirsByVisualType", {}).get(
        visual_type,
        cfg.get("defaultSearchDirs", []),
    )
    allowed_exts = set()
    if "image" in required_kinds:
        allowed_exts.update(cfg["imageExtensions"])
    if "video" in required_kinds:
        allowed_exts.update(cfg["videoExtensions"])

    for directory_name in dirs:
        directory = work_dir / str(directory_name)
        if not directory.is_dir():
            continue
        for candidate in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            if not candidate.is_file():
                continue
            if candidate.stem != scene_id or candidate.suffix.lower() not in allowed_exts:
                continue
            rel = relative_inside(candidate, work_dir)
            if rel is None:
                continue
            kind = classify_kind(candidate, cfg)
            if kind is None or kind not in required_kinds:
                continue
            return {
                "status": "resolved",
                "kind": kind,
                "relativePath": rel,
                "source": "scene-id-convention",
                "reason": f"{directory_name}/{candidate.name}",
            }
    return None


def resolve_scene(scene: dict, work_dir: Path, cfg: dict) -> dict:
    item = dict(scene)
    direction = scene.get("visualDirection") or {}
    visual_type = str(direction.get("visualType") or "presenter")
    query = str(direction.get("assetQuery") or scene.get("caption") or "").strip()

    explicit = explicit_overlay(scene, work_dir, cfg)
    if explicit and explicit["status"] == "resolved":
        if query:
            explicit["query"] = query
        item["assetResolution"] = explicit
        return item

    required_kinds = list(
        cfg.get("requiredKindsByVisualType", {}).get(visual_type, [])
    )
    if not required_kinds:
        item["assetResolution"] = {
            "status": "not-required",
            "reason": f"visual-type:{visual_type}",
        }
        return item

    scene_id = str(scene.get("id") or "").strip()
    resolved = convention_asset(
        scene_id,
        visual_type,
        work_dir,
        cfg,
        required_kinds,
    )
    if resolved:
        if query:
            resolved["query"] = query
        item["assetResolution"] = resolved
        return item

    missing = {
        "status": "missing",
        "requiredKinds": required_kinds,
        "reason": (
            explicit["reason"]
            if explicit and explicit.get("reason")
            else "no-local-asset"
        ),
    }
    if query:
        missing["query"] = query
    item["assetResolution"] = missing
    return item


def resolve(plan: dict, work_dir: Path, cfg: dict) -> dict:
    out = dict(plan)
    scenes = [
        resolve_scene(scene, work_dir, cfg)
        for scene in (plan.get("scenes") or [])
    ]
    out["scenes"] = scenes

    counts: dict[str, int] = {}
    for scene in scenes:
        status = str(scene["assetResolution"]["status"])
        counts[status] = counts.get(status, 0) + 1

    out["assetResolver"] = {
        "version": int(cfg.get("version") or 1),
        "source": "local-asset-resolver-v1",
        "counts": counts,
    }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-plan", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plan_path = args.scene_plan.expanduser().resolve()
    work_dir = (
        args.work_dir.expanduser().resolve()
        if args.work_dir
        else plan_path.parent
    )
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    out = resolve(plan, work_dir, cfg)

    destination = args.output or work_dir / "asset-resolver-plan.json"
    destination.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    counts = out["assetResolver"]["counts"]
    summary = ", ".join(
        f"{key}={value}" for key, value in sorted(counts.items())
    )
    print(f"asset-resolver: {summary or 'no-scenes'}")
    print(f"- plan: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
