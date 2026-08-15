from __future__ import annotations

import os
from pathlib import Path

import httpx
import streamlit as st


API_URL = os.getenv("COORDINATOR_URL", "http://coordinator:8000")
SAMPLE_RESUME = Path(os.getenv("SAMPLE_RESUME_PATH", "/app/data/sample/sample_resume.txt"))

st.set_page_config(page_title="SkillMesh", page_icon="🧭", layout="wide")


def api_get(path: str, timeout: float = 15.0):
    with httpx.Client(timeout=timeout) as client:
        response = client.get(f"{API_URL}{path}")
        response.raise_for_status()
        return response.json()


def api_post(path: str, payload: dict, timeout: float = 60.0):
    with httpx.Client(timeout=timeout) as client:
        response = client.post(f"{API_URL}{path}", json=payload)
        response.raise_for_status()
        return response.json()


def show_nodes() -> None:
    st.sidebar.subheader("Distributed nodes")
    try:
        for node in api_get("/api/nodes", timeout=5.0):
            icon = "🟢" if node.get("available") else "🔴"
            st.sidebar.write(f"{icon} {node['name']}")
    except Exception:
        st.sidebar.error("Coordinator unavailable")


show_nodes()
st.title("🧭 SkillMesh")
st.caption("Federated career matching and evidence-grounded skill-gap analysis")
st.info("The bundled corpus is synthetic demonstration data. Import pinned official O*NET and ESCO exports before research evaluation.")

if "resume_id" not in st.session_state:
    st.session_state.resume_id = None
if "career_matches" not in st.session_state:
    st.session_state.career_matches = []
if "analysis" not in st.session_state:
    st.session_state.analysis = None

default_resume = SAMPLE_RESUME.read_text(encoding="utf-8") if SAMPLE_RESUME.exists() else ""
st.subheader("1. Add a résumé")
upload_tab, text_tab = st.tabs(["Upload", "Paste text"])

with upload_tab:
    uploaded = st.file_uploader("PDF, DOCX, TXT, or Markdown", type=["pdf", "docx", "txt", "md"])
    if st.button("Process uploaded résumé", disabled=uploaded is None, use_container_width=True):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{API_URL}/api/resumes/upload",
                    files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                )
                response.raise_for_status()
                record = response.json()
            st.session_state.resume_id = record["resume_id"]
            st.session_state.analysis = None
            st.success(f"Detected {len(record['skills'])} skills.")
        except Exception as error:
            st.error(f"Unable to process résumé: {error}")

with text_tab:
    resume_text = st.text_area("Résumé text", value=default_resume, height=220)
    if st.button("Process résumé text", type="primary", use_container_width=True):
        try:
            record = api_post("/api/resumes/text", {"text": resume_text})
            st.session_state.resume_id = record["resume_id"]
            st.session_state.analysis = None
            st.success(f"Detected {len(record['skills'])} skills.")
        except Exception as error:
            st.error(f"Unable to process résumé: {error}")

if st.session_state.resume_id:
    st.subheader("2. Discover career matches")
    if st.button("Rank occupations", use_container_width=True):
        try:
            with st.spinner("Querying O*NET and ESCO nodes..."):
                result = api_post(
                    "/api/career-matches",
                    {"resume_id": st.session_state.resume_id, "top_k": 5},
                    timeout=60.0,
                )
            st.session_state.career_matches = result["matches"]
            st.session_state.detected_skills = result["detected_skills"]
        except Exception as error:
            st.error(f"Unable to rank occupations: {error}")

if st.session_state.get("detected_skills"):
    with st.expander("Detected résumé skills", expanded=False):
        for skill in st.session_state.detected_skills:
            st.markdown(f"**{skill['label']}** — {skill['confidence']:.0%}  \n{skill['evidence']}")

if st.session_state.career_matches:
    columns = st.columns(min(5, len(st.session_state.career_matches)))
    for column, match in zip(columns, st.session_state.career_matches):
        with column:
            st.metric(match["title"], f"{match['match_score']:.1f}%")
            st.caption("Strengths: " + (", ".join(match["top_strengths"]) or "None evidenced"))

    options = {item["title"]: item["occupation_id"] for item in st.session_state.career_matches}
    target_title = st.selectbox("Choose a target occupation", options=list(options))
    max_courses = st.slider("Maximum courses", 1, 6, 4)
    level = st.selectbox("Preferred course level", ["beginner", "intermediate"])
    if st.button("Generate full skill-gap analysis", type="primary", use_container_width=True):
        try:
            with st.spinner("Retrieving evidence and building the roadmap..."):
                st.session_state.analysis = api_post(
                    "/api/analyses",
                    {
                        "resume_id": st.session_state.resume_id,
                        "target_occupation_id": options[target_title],
                        "maximum_courses": max_courses,
                        "preferred_level": level,
                        "maximum_duration_hours": 40,
                    },
                    timeout=90.0,
                )
        except Exception as error:
            st.error(f"Unable to generate analysis: {error}")

analysis = st.session_state.analysis
if analysis:
    st.divider()
    st.subheader(f"Skill-gap report: {analysis['target_occupation']}")
    score_col, coverage_col, mode_col = st.columns(3)
    score_col.metric("Career match", f"{analysis['match_score']:.1f}%")
    coverage_col.metric("Evidence coverage", f"{analysis['coverage_score']:.1f}%")
    mode_col.metric("Generation", analysis["generation_mode"])
    st.progress(min(analysis["match_score"] / 100, 1.0))
    st.write(analysis["summary"])

    if analysis["degraded_sources"]:
        st.warning("Degraded mode — unavailable: " + ", ".join(analysis["degraded_sources"]))
    for warning in analysis["warnings"]:
        st.caption("⚠️ " + warning)

    strengths_col, gaps_col = st.columns(2)
    with strengths_col:
        st.markdown("#### Evidenced strengths")
        if not analysis["strengths"]:
            st.write("No strongly evidenced target skills.")
        for item in analysis["strengths"]:
            st.success(f"{item['label']} — {item['user_confidence']:.0%}")
            st.caption(item["resume_evidence"])
    with gaps_col:
        st.markdown("#### Priority gaps")
        if not analysis["gaps"]:
            st.write("No high-priority gaps detected.")
        for item in analysis["gaps"][:8]:
            st.error(f"{item['label']} — priority {item['gap_priority']:.2f}")

    st.markdown("#### Learning roadmap")
    if not analysis["courses"]:
        st.write("No course recommendations were required or available.")
    for index, course in enumerate(analysis["courses"], start=1):
        metadata = course["metadata"]
        st.markdown(f"**{index}. {course['title']}** — {metadata['level']}, {metadata['duration_hours']} hours")
        st.caption("Addresses: " + ", ".join(course["addresses"]))

    with st.expander(f"Sources and citations ({len(analysis['citations'])})"):
        for citation in analysis["citations"]:
            st.markdown(f"**{citation['title']}** — `{citation['evidence_id']}`")
            st.write(citation["text"])
            if citation.get("source_url"):
                st.link_button("Open source landing page", citation["source_url"])
