from __future__ import annotations

import unittest
from pathlib import Path

from packages.core.matching import analyze_gap, merge_requirements, rank_courses
from packages.core.retrieval import HybridIndex, load_documents
from packages.core.skills import extract_skills, load_skill_catalog


ROOT = Path(__file__).resolve().parents[1]


class SkillExtractionTests(unittest.TestCase):
    def test_extracts_alias_across_line_break(self) -> None:
        catalog = load_skill_catalog(ROOT / "data/sample/canonical_skills.json")
        text = "Built Python services and configured GitHub\nActions for delivery. Used Docker."
        detected = {item["skill_id"] for item in extract_skills(text, catalog)}
        self.assertTrue({"python", "ci_cd", "docker"}.issubset(detected))


class RetrievalTests(unittest.TestCase):
    def test_metadata_filter_isolation(self) -> None:
        index = HybridIndex(load_documents(ROOT / "data/sample/onet_documents.json"))
        results = index.search(
            "monitoring",
            top_k=50,
            document_types=["skill_requirement"],
            filters={"canonical_occupation_id": "devops_engineer"},
        )
        self.assertGreater(len(results), 5)
        self.assertTrue(all(item["metadata"]["canonical_occupation_id"] == "devops_engineer" for item in results))


class MatchingTests(unittest.TestCase):
    def setUp(self) -> None:
        resume = (ROOT / "data/sample/sample_resume.txt").read_text(encoding="utf-8")
        self.skills = extract_skills(resume, load_skill_catalog(ROOT / "data/sample/canonical_skills.json"))
        filters = {"canonical_occupation_id": "devops_engineer"}
        onet = HybridIndex(load_documents(ROOT / "data/sample/onet_documents.json"))
        esco = HybridIndex(load_documents(ROOT / "data/sample/esco_documents.json"))
        self.evidence = onet.search("devops", 50, ["occupation", "skill_requirement"], filters)
        self.evidence += esco.search("devops", 50, ["occupation", "skill_requirement"], filters)

    def test_gap_analysis_is_deterministic(self) -> None:
        requirements = merge_requirements(self.evidence)
        analysis = analyze_gap(requirements, self.skills)
        strength_ids = {item["skill_id"] for item in analysis["strengths"]}
        gap_ids = {item["skill_id"] for item in analysis["gaps"]}
        self.assertTrue({"docker", "ci_cd", "cloud_platforms", "git"}.issubset(strength_ids))
        self.assertTrue({"kubernetes", "infrastructure_as_code", "monitoring"}.issubset(gap_ids))
        self.assertGreater(analysis["match_score"], 30)
        self.assertEqual(analysis["coverage_score"], 100.0)

    def test_course_set_cover(self) -> None:
        analysis = analyze_gap(merge_requirements(self.evidence), self.skills)
        course_index = HybridIndex(load_documents(ROOT / "data/sample/course_documents.json"))
        courses = course_index.search(" ".join(item["label"] for item in analysis["gaps"]), 30, ["course"])
        selected = rank_courses(courses, analysis["gaps"], 4, "beginner", 40)
        ids = [item["evidence_id"] for item in selected]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertLessEqual(len(ids), 4)


if __name__ == "__main__":
    unittest.main()
