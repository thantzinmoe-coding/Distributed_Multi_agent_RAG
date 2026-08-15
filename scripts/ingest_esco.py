"""Convert ESCO occupation, skill, and relation CSV exports to SkillMesh JSON."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def pick(row: dict[str, str], *candidates: str) -> str:
    lowered = {key.lower(): value for key, value in row.items()}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--occupations", type=Path, required=True)
    parser.add_argument("--skills", type=Path, required=True)
    parser.add_argument("--relations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="pinned-esco-export")
    parser.add_argument("--limit-occupations", type=int, default=0)
    args = parser.parse_args()

    occupation_rows = read_csv(args.occupations)
    if args.limit_occupations:
        occupation_rows = occupation_rows[: args.limit_occupations]
    occupations = {
        pick(row, "conceptUri", "conceptURI", "uri"): {
            "title": pick(row, "preferredLabel", "preferred label", "title"),
            "description": pick(row, "description", "scopeNote", "definition"),
        }
        for row in occupation_rows
        if pick(row, "conceptUri", "conceptURI", "uri")
    }
    skills = {
        pick(row, "conceptUri", "conceptURI", "uri"): pick(row, "preferredLabel", "preferred label", "title")
        for row in read_csv(args.skills)
        if pick(row, "conceptUri", "conceptURI", "uri")
    }
    url = "https://esco.ec.europa.eu/en/use-esco"
    documents: list[dict] = []
    for uri, occupation in occupations.items():
        occupation_id = slug(occupation["title"])
        documents.append(
            {
                "evidence_id": f"esco:{args.version}:occupation:{slug(uri)}",
                "source": "ESCO",
                "title": occupation["title"],
                "text": occupation["description"] or occupation["title"],
                "document_type": "occupation",
                "source_url": uri or url,
                "source_version": args.version,
                "license": "Verify the reuse notice included with the ESCO export",
                "metadata": {"canonical_occupation_id": occupation_id, "occupation_title": occupation["title"], "source_occupation_id": uri},
            }
        )

    for row in read_csv(args.relations):
        occupation_uri = pick(row, "occupationUri", "occupationURI", "occupation")
        skill_uri = pick(row, "skillUri", "skillURI", "skill")
        if occupation_uri not in occupations or skill_uri not in skills:
            continue
        relationship = pick(row, "relationType", "relationshipType", "type").lower()
        importance = 1.0 if "essential" in relationship else 0.6
        occupation = occupations[occupation_uri]
        label = skills[skill_uri]
        documents.append(
            {
                "evidence_id": f"esco:{args.version}:{slug(occupation_uri)}:skill:{slug(skill_uri)}",
                "source": "ESCO",
                "title": f"{occupation['title']} — {label}",
                "text": f"ESCO lists {label} as a {relationship or 'related'} skill for {occupation['title']}.",
                "document_type": "skill_requirement",
                "source_url": skill_uri or url,
                "source_version": args.version,
                "license": "Verify the reuse notice included with the ESCO export",
                "metadata": {
                    "canonical_occupation_id": slug(occupation["title"]),
                    "occupation_title": occupation["title"],
                    "canonical_skill_id": slug(label),
                    "skill_label": label,
                    "importance": importance,
                    "requirement": relationship or "related",
                    "source_occupation_id": occupation_uri,
                    "source_skill_id": skill_uri,
                    "mapping_reviewed": False,
                },
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(documents, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(documents)} ESCO records to {args.output}")


if __name__ == "__main__":
    main()
