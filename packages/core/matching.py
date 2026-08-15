from __future__ import annotations

from typing import Any


def merge_requirements(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for record in evidence:
        metadata = record.get("metadata", {})
        skill_id = metadata.get("canonical_skill_id")
        if not skill_id or record.get("document_type") != "skill_requirement":
            continue
        weight = float(metadata.get("importance", 0.6))
        current = merged.setdefault(
            skill_id,
            {
                "skill_id": skill_id,
                "label": metadata.get("skill_label", skill_id.replace("_", " ").title()),
                "importance": 0.0,
                "sources": set(),
                "evidence_ids": [],
            },
        )
        current["importance"] = max(current["importance"], weight)
        current["sources"].add(record["source"])
        current["evidence_ids"].append(record["evidence_id"])

    result = []
    for value in merged.values():
        if len(value["sources"]) > 1:
            value["importance"] = min(1.0, value["importance"] + 0.05)
        value["sources"] = sorted(value["sources"])
        value["importance"] = round(value["importance"], 3)
        result.append(value)
    return sorted(result, key=lambda item: (-item["importance"], item["label"]))


def analyze_gap(requirements: list[dict[str, Any]], user_skills: list[dict[str, Any]]) -> dict[str, Any]:
    user_lookup = {item["skill_id"]: item for item in user_skills}
    denominator = sum(item["importance"] for item in requirements) or 1.0
    numerator = 0.0
    strengths, partial, gaps = [], [], []

    for requirement in requirements:
        user = user_lookup.get(requirement["skill_id"])
        confidence = float(user["confidence"]) if user else 0.0
        numerator += requirement["importance"] * confidence
        item = {
            **requirement,
            "user_confidence": round(confidence, 3),
            "gap_priority": round(requirement["importance"] * (1 - confidence), 3),
            "resume_evidence": user.get("evidence", "No explicit résumé evidence found.") if user else "No explicit résumé evidence found.",
        }
        if confidence >= 0.75:
            strengths.append(item)
        elif confidence >= 0.35:
            partial.append(item)
        else:
            gaps.append(item)

    gaps.sort(key=lambda item: (-item["gap_priority"], item["label"]))
    coverage = sum(item["importance"] for item in requirements if item["evidence_ids"]) / denominator
    return {
        "match_score": round(100 * numerator / denominator, 1),
        "coverage_score": round(100 * coverage, 1),
        "strengths": strengths,
        "partial_skills": partial,
        "gaps": gaps,
    }


def rank_courses(
    courses: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    maximum_courses: int,
    preferred_level: str,
    maximum_duration_hours: int,
) -> list[dict[str, Any]]:
    gap_weight = {item["skill_id"]: item["gap_priority"] for item in gaps}
    remaining = set(gap_weight)
    selected: list[dict[str, Any]] = []

    while remaining and len(selected) < maximum_courses:
        best: tuple[float, dict[str, Any]] | None = None
        for course in courses:
            if any(existing["evidence_id"] == course["evidence_id"] for existing in selected):
                continue
            metadata = course.get("metadata", {})
            duration = int(metadata.get("duration_hours", 0))
            if duration > maximum_duration_hours:
                continue
            skills = set(metadata.get("skill_ids", []))
            covered = skills.intersection(remaining)
            if not covered:
                continue
            coverage_score = sum(gap_weight[skill] for skill in covered)
            level_bonus = 0.15 if metadata.get("level") == preferred_level else 0.05
            score = coverage_score + level_bonus
            if best is None or score > best[0]:
                best = (score, {**course, "addresses": sorted(covered), "course_score": round(score, 3)})
        if best is None:
            break
        selected.append(best[1])
        remaining.difference_update(best[1]["addresses"])
    return selected
