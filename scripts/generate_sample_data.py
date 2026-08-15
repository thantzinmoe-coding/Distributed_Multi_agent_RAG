"""Generate the small, clearly labelled corpus used by the local demo.

The records are synthetic examples shaped like O*NET and ESCO data. They are
not quotations or official occupation profiles. Replace them with pinned
official exports before performing research evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample"
MANIFESTS = ROOT / "data" / "manifests"


SKILLS = [
    {"id": "python", "label": "Python", "aliases": ["Python programming"]},
    {"id": "git", "label": "Git", "aliases": ["version control", "GitHub"]},
    {"id": "linux", "label": "Linux", "aliases": ["Linux administration", "Unix"]},
    {"id": "docker", "label": "Docker", "aliases": ["containers", "containerization"]},
    {"id": "kubernetes", "label": "Kubernetes", "aliases": ["container orchestration", "K8s"]},
    {"id": "ci_cd", "label": "CI/CD", "aliases": ["continuous integration", "GitHub Actions", "continuous delivery"]},
    {"id": "cloud_platforms", "label": "Cloud platforms", "aliases": ["AWS", "Azure", "Google Cloud", "GCP"]},
    {"id": "infrastructure_as_code", "label": "Infrastructure as code", "aliases": ["Terraform", "Ansible", "IaC"]},
    {"id": "monitoring", "label": "Monitoring and observability", "aliases": ["Prometheus", "Grafana", "observability"]},
    {"id": "networking", "label": "Computer networking", "aliases": ["TCP/IP", "DNS", "network administration"]},
    {"id": "scripting", "label": "Automation scripting", "aliases": ["Bash", "PowerShell", "shell scripting"]},
    {"id": "security", "label": "Security practices", "aliases": ["secure coding", "information security"]},
    {"id": "api_design", "label": "API design", "aliases": ["REST API", "RESTful APIs", "FastAPI"]},
    {"id": "sql", "label": "SQL", "aliases": ["PostgreSQL", "MySQL", "relational databases"]},
    {"id": "testing", "label": "Software testing", "aliases": ["unit testing", "pytest", "integration testing"]},
    {"id": "statistics", "label": "Statistics", "aliases": ["statistical analysis"]},
    {"id": "data_visualization", "label": "Data visualization", "aliases": ["Power BI", "Tableau", "Matplotlib"]},
    {"id": "spreadsheets", "label": "Spreadsheets", "aliases": ["Excel", "Google Sheets"]},
    {"id": "communication", "label": "Communication", "aliases": ["technical communication", "presentation skills"]},
    {"id": "network_security", "label": "Network security", "aliases": ["firewall", "intrusion detection"]},
    {"id": "incident_response", "label": "Incident response", "aliases": ["security incident handling", "SOC operations"]},
    {"id": "risk_assessment", "label": "Risk assessment", "aliases": ["security risk analysis", "threat assessment"]},
    {"id": "database_admin", "label": "Database administration", "aliases": ["DBA", "database management"]},
    {"id": "backup_recovery", "label": "Backup and recovery", "aliases": ["disaster recovery", "database backup"]},
]


OCCUPATIONS = [
    {
        "id": "devops_engineer",
        "title": "DevOps Engineer",
        "description": "Builds automated delivery systems and maintains reliable development and production environments.",
        "skills": {"linux": .90, "docker": .88, "ci_cd": .92, "cloud_platforms": .82, "infrastructure_as_code": .86, "kubernetes": .80, "monitoring": .78, "networking": .70, "scripting": .82, "security": .66, "git": .76},
    },
    {
        "id": "backend_developer",
        "title": "Backend Developer",
        "description": "Designs and maintains server-side applications, APIs, data access, and automated tests.",
        "skills": {"python": .92, "api_design": .90, "sql": .82, "git": .72, "testing": .78, "docker": .62, "security": .68, "communication": .55},
    },
    {
        "id": "data_analyst",
        "title": "Data Analyst",
        "description": "Transforms data into reports, visualizations, and evidence that supports business decisions.",
        "skills": {"sql": .92, "spreadsheets": .82, "statistics": .84, "data_visualization": .90, "python": .70, "communication": .74},
    },
    {
        "id": "cybersecurity_analyst",
        "title": "Cybersecurity Analyst",
        "description": "Monitors threats, investigates incidents, and helps protect systems and networks.",
        "skills": {"network_security": .94, "incident_response": .90, "linux": .72, "scripting": .66, "risk_assessment": .86, "security": .94, "communication": .62, "networking": .82},
    },
    {
        "id": "database_administrator",
        "title": "Database Administrator",
        "description": "Operates database platforms, protects data, monitors performance, and plans recovery.",
        "skills": {"sql": .94, "database_admin": .96, "backup_recovery": .90, "monitoring": .76, "linux": .64, "security": .78, "scripting": .58, "communication": .52},
    },
]


COURSES = [
    ("C001", "Linux Administration Essentials", "linux", "beginner", 10),
    ("C002", "Docker Fundamentals", "docker", "beginner", 8),
    ("C003", "CI/CD with GitHub Actions", "ci_cd", "beginner", 8),
    ("C004", "Terraform and Infrastructure as Code", "infrastructure_as_code", "intermediate", 12),
    ("C005", "Kubernetes Fundamentals", "kubernetes", "intermediate", 14),
    ("C006", "Monitoring with Prometheus and Grafana", "monitoring", "intermediate", 10),
    ("C007", "Cloud Platform Foundations", "cloud_platforms", "beginner", 14),
    ("C008", "Practical Computer Networking", "networking", "beginner", 12),
    ("C009", "Secure Software Practices", "security", "beginner", 8),
    ("C010", "REST API Design with Python", "api_design", "intermediate", 10),
    ("C011", "SQL and Relational Data", "sql", "beginner", 12),
    ("C012", "Automated Testing with pytest", "testing", "beginner", 7),
    ("C013", "Applied Statistics", "statistics", "beginner", 15),
    ("C014", "Data Visualization Fundamentals", "data_visualization", "beginner", 9),
    ("C015", "Security Incident Response", "incident_response", "intermediate", 14),
    ("C016", "Database Backup and Recovery", "backup_recovery", "intermediate", 12),
]


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def source_documents(source: str) -> list[dict]:
    is_onet = source == "O*NET SAMPLE"
    base_url = "https://www.onetcenter.org/database.html" if is_onet else "https://esco.ec.europa.eu/en/use-esco"
    license_name = "CC BY 4.0" if is_onet else "See official ESCO reuse notice"
    documents: list[dict] = []
    skill_labels = {skill["id"]: skill["label"] for skill in SKILLS}
    for occupation in OCCUPATIONS:
        documents.append(
            {
                "evidence_id": f"{'onet' if is_onet else 'esco'}:sample:occupation:{occupation['id']}",
                "source": source,
                "title": occupation["title"],
                "text": occupation["description"] + " This is synthetic demonstration data, not an official occupation profile.",
                "document_type": "occupation",
                "source_url": base_url,
                "source_version": "skillmesh-sample-1",
                "license": license_name,
                "metadata": {"canonical_occupation_id": occupation["id"], "occupation_title": occupation["title"], "sample": True},
            }
        )
        for skill_id, original_weight in occupation["skills"].items():
            weight = original_weight if is_onet else max(.5, min(1.0, original_weight + (-.04 if original_weight > .8 else .04)))
            requirement = "essential" if weight >= .75 else "optional"
            label = skill_labels[skill_id]
            documents.append(
                {
                    "evidence_id": f"{'onet' if is_onet else 'esco'}:sample:{occupation['id']}:skill:{skill_id}",
                    "source": source,
                    "title": f"{occupation['title']} — {label}",
                    "text": f"In the SkillMesh synthetic {source} profile, {label} is a {requirement} skill for {occupation['title']} with normalized importance {weight:.2f}.",
                    "document_type": "skill_requirement",
                    "source_url": base_url,
                    "source_version": "skillmesh-sample-1",
                    "license": license_name,
                    "metadata": {
                        "canonical_occupation_id": occupation["id"],
                        "occupation_title": occupation["title"],
                        "canonical_skill_id": skill_id,
                        "skill_label": label,
                        "importance": round(weight, 2),
                        "requirement": requirement,
                        "sample": True,
                    },
                }
            )
    return documents


def course_documents() -> list[dict]:
    result = []
    labels = {skill["id"]: skill["label"] for skill in SKILLS}
    for course_id, title, skill_id, level, duration in COURSES:
        result.append(
            {
                "evidence_id": f"course:sample:{course_id}",
                "source": "SkillMesh Course Catalog",
                "title": title,
                "text": f"A {level} learning resource covering {labels[skill_id]}. Estimated study time: {duration} hours.",
                "document_type": "course",
                "source_url": "https://example.invalid/skillmesh-course-catalog",
                "source_version": "sample-1",
                "license": "Synthetic demo data",
                "metadata": {"course_id": course_id, "skill_ids": [skill_id], "level": level, "duration_hours": duration, "provider": "SkillMesh Demo"},
            }
        )
    return result


def main() -> None:
    SAMPLE.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    dump(SAMPLE / "canonical_skills.json", SKILLS)
    dump(SAMPLE / "occupations.json", [{"id": item["id"], "title": item["title"]} for item in OCCUPATIONS])
    dump(SAMPLE / "onet_documents.json", source_documents("O*NET SAMPLE"))
    dump(SAMPLE / "esco_documents.json", source_documents("ESCO SAMPLE"))
    dump(SAMPLE / "course_documents.json", course_documents())
    for name in ("onet", "esco", "courses"):
        dump(
            MANIFESTS / f"{name}.json",
            {
                "dataset": f"{name}-sample",
                "version": "skillmesh-sample-1",
                "synthetic": True,
                "warning": "Replace this corpus with a pinned official export before research evaluation.",
            },
        )
    print(f"Generated SkillMesh sample data in {SAMPLE}")


if __name__ == "__main__":
    main()
