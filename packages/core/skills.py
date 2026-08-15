from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_skill_catalog(path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _evidence_sentence(text: str, start: int, end: int) -> str:
    left = max(text.rfind(".", 0, start), text.rfind("\n", 0, start))
    right_period = text.find(".", end)
    right_line = text.find("\n", end)
    rights = [value for value in (right_period, right_line) if value >= 0]
    right = min(rights) if rights else min(len(text), end + 180)
    return " ".join(text[left + 1 : right + 1].strip().split())[:300]


def extract_skills(text: str, catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    detected: dict[str, dict[str, Any]] = {}
    for skill in catalog:
        aliases = [skill["label"], *skill.get("aliases", [])]
        aliases.sort(key=len, reverse=True)
        for alias in aliases:
            escaped_alias = re.escape(alias).replace(r"\ ", r"\s+")
            pattern = re.compile(rf"(?<!\w){escaped_alias}(?!\w)", re.IGNORECASE)
            match = pattern.search(text)
            if not match:
                continue
            confidence = 0.96 if alias.lower() == skill["label"].lower() else 0.87
            candidate = {
                "skill_id": skill["id"],
                "label": skill["label"],
                "confidence": confidence,
                "evidence": _evidence_sentence(text, match.start(), match.end()),
                "matched_alias": match.group(0),
            }
            if skill["id"] not in detected or confidence > detected[skill["id"]]["confidence"]:
                detected[skill["id"]] = candidate
            break
    return sorted(detected.values(), key=lambda item: (-item["confidence"], item["label"]))
