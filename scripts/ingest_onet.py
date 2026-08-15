"""Convert selected files from an extracted O*NET database into SkillMesh JSON.

This adapter intentionally preserves source identifiers and does not claim that
automatic label slugs are a reviewed O*NET/ESCO crosswalk. Review mappings before
using the output for evaluation.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--occupation-data", type=Path, required=True)
    parser.add_argument("--skills", type=Path, required=True)
    parser.add_argument("--tasks", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="pinned-onet-export")
    parser.add_argument("--occupation-codes", help="Optional comma-separated O*NET-SOC codes")
    args = parser.parse_args()

    selected = set(filter(None, (args.occupation_codes or "").split(",")))
    occupations = {
        row["O*NET-SOC Code"]: row
        for row in read_tsv(args.occupation_data)
        if not selected or row["O*NET-SOC Code"] in selected
    }
    documents: list[dict] = []
    url = "https://www.onetcenter.org/database.html"

    for code, row in occupations.items():
        occupation_id = slug(row["Title"])
        documents.append(
            {
                "evidence_id": f"onet:{args.version}:occupation:{code}",
                "source": "O*NET",
                "title": row["Title"],
                "text": row.get("Description", ""),
                "document_type": "occupation",
                "source_url": url,
                "source_version": args.version,
                "license": "CC BY 4.0; verify export notices",
                "metadata": {"canonical_occupation_id": occupation_id, "occupation_title": row["Title"], "source_occupation_id": code},
            }
        )

    skill_values: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in read_tsv(args.skills):
        code = row.get("O*NET-SOC Code", "")
        if code not in occupations:
            continue
        try:
            value = float(row.get("Data Value", "0"))
        except ValueError:
            continue
        scale = row.get("Scale ID", "")
        normalized = value / 5.0 if scale in {"IM", "LV"} else min(1.0, value / 100.0)
        skill_values[(code, row.get("Element Name", "Unknown skill"))].append(normalized)

    for (code, label), values in skill_values.items():
        occupation = occupations[code]
        occupation_id = slug(occupation["Title"])
        skill_id = slug(label)
        importance = max(values)
        documents.append(
            {
                "evidence_id": f"onet:{args.version}:{code}:skill:{skill_id}",
                "source": "O*NET",
                "title": f"{occupation['Title']} — {label}",
                "text": f"O*NET associates {label} with {occupation['Title']} in export {args.version}.",
                "document_type": "skill_requirement",
                "source_url": url,
                "source_version": args.version,
                "license": "CC BY 4.0; verify export notices",
                "metadata": {
                    "canonical_occupation_id": occupation_id,
                    "occupation_title": occupation["Title"],
                    "canonical_skill_id": skill_id,
                    "skill_label": label,
                    "importance": round(max(0.05, min(1.0, importance)), 3),
                    "source_occupation_id": code,
                    "mapping_reviewed": False,
                },
            }
        )

    if args.tasks:
        grouped_tasks: dict[str, list[str]] = defaultdict(list)
        for row in read_tsv(args.tasks):
            code = row.get("O*NET-SOC Code", "")
            if code in occupations and row.get("Task"):
                grouped_tasks[code].append(row["Task"])
        for code, tasks in grouped_tasks.items():
            occupation = occupations[code]
            documents.append(
                {
                    "evidence_id": f"onet:{args.version}:{code}:tasks",
                    "source": "O*NET",
                    "title": f"{occupation['Title']} — tasks",
                    "text": " ".join(tasks[:20]),
                    "document_type": "task",
                    "source_url": url,
                    "source_version": args.version,
                    "license": "CC BY 4.0; verify export notices",
                    "metadata": {"canonical_occupation_id": slug(occupation["Title"]), "occupation_title": occupation["Title"], "source_occupation_id": code},
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(documents, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(documents)} O*NET records to {args.output}")


if __name__ == "__main__":
    main()
