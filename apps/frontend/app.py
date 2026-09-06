from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any

import httpx
import streamlit as st


API_URL = os.getenv("COORDINATOR_URL", "http://coordinator:8000")
SAMPLE_RESUME = Path(os.getenv("SAMPLE_RESUME_PATH", "/app/data/sample/sample_resume.txt"))

st.set_page_config(page_title="SkillMesh", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --sm-primary: #4f46e5;
            --sm-primary-soft: #eef2ff;
            --sm-text: #172033;
            --sm-muted: #667085;
            --sm-border: #e4e7ec;
            --sm-success: #15803d;
            --sm-success-soft: #ecfdf3;
            --sm-warning: #b54708;
            --sm-warning-soft: #fffaeb;
        }
        .block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem;}
        [data-testid="stHeader"] {background: transparent;}
        [data-testid="stSidebar"] {border-right: 1px solid var(--sm-border);}
        h1, h2, h3 {color: var(--sm-text); letter-spacing: -0.025em;}
        .sm-hero {
            padding: 1.3rem 1.5rem; border: 1px solid #d9ddff; border-radius: 20px;
            background: linear-gradient(135deg, #f8f9ff 0%, #eef2ff 55%, #f8fafc 100%);
            margin-bottom: 1.25rem;
        }
        .sm-eyebrow {color: var(--sm-primary); font-size: .78rem; font-weight: 750; letter-spacing: .12em; text-transform: uppercase;}
        .sm-hero h1 {font-size: 2.15rem; margin: .25rem 0 .3rem; color: #172033 !important;}
        .sm-hero p {color: #667085 !important; margin: 0; max-width: 730px;}
        button[kind="primary"]:not(:disabled) {background: var(--sm-primary) !important; border-color: var(--sm-primary) !important;}
        .stTabs [data-baseweb="tab"][aria-selected="true"] {color: #818cf8 !important;}
        .stTabs [data-baseweb="tab-highlight"] {background-color: var(--sm-primary) !important;}
        .sm-stepper {display: grid; grid-template-columns: repeat(3, 1fr); gap: .65rem; margin: 1rem 0 1.75rem;}
        .sm-step {display: flex; align-items: center; gap: .65rem; color: #98a2b3; border-bottom: 3px solid #eaecf0; padding: .55rem .25rem; font-weight: 650;}
        .sm-step.active {color: var(--sm-primary); border-color: var(--sm-primary);}
        .sm-step.done {color: var(--sm-success); border-color: #86efac;}
        .sm-step-number {display: inline-grid; place-items: center; width: 25px; height: 25px; border: 1px solid currentColor; border-radius: 50%; font-size: .78rem;}
        .sm-kicker {color: var(--sm-primary); font-size: .8rem; font-weight: 750; text-transform: uppercase; letter-spacing: .08em; margin-bottom: .15rem;}
        .sm-section-copy {color: var(--sm-muted); margin-top: -.5rem; margin-bottom: 1rem;}
        .sm-chip {display: inline-block; padding: .28rem .58rem; margin: .18rem .2rem .18rem 0; border-radius: 999px; background: var(--sm-primary-soft); color: #3730a3; font-size: .82rem; font-weight: 650;}
        .sm-chip.success {background: var(--sm-success-soft); color: var(--sm-success);}
        .sm-chip.warning {background: var(--sm-warning-soft); color: var(--sm-warning);}
        .sm-skill {margin: .65rem 0 .85rem;}
        .sm-skill-head {display: flex; justify-content: space-between; gap: 1rem; font-size: .88rem; margin-bottom: .3rem;}
        .sm-skill-name {font-weight: 680; color: var(--sm-text);}
        .sm-skill-value {color: var(--sm-muted);}
        .sm-track {height: 8px; border-radius: 99px; background: #f2f4f7; overflow: hidden;}
        .sm-fill {height: 100%; border-radius: 99px; background: var(--sm-primary);}
        .sm-fill.strong {background: #22c55e;}
        .sm-fill.developing {background: #f59e0b;}
        .sm-fill.gap {background: #8b5cf6;}
        .sm-timeline {display: grid; grid-template-columns: 82px 22px 1fr; gap: .35rem .65rem; align-items: stretch; margin: .2rem 0;}
        .sm-week {color: var(--sm-primary); font-size: .82rem; font-weight: 750; padding-top: .85rem; text-align: right;}
        .sm-line {position: relative; border-left: 2px solid #c7d2fe; margin-left: 10px;}
        .sm-dot {position: absolute; width: 12px; height: 12px; border-radius: 50%; background: var(--sm-primary); left: -7px; top: 1.05rem; box-shadow: 0 0 0 4px #eef2ff;}
        .sm-course {border: 1px solid var(--sm-border); border-radius: 14px; padding: .85rem 1rem; margin: .35rem 0 .8rem; background: #fff;}
        .sm-course-title {font-weight: 750; color: var(--sm-text);}
        .sm-course-meta {color: var(--sm-muted); font-size: .84rem; margin-top: .2rem;}
        .sm-privacy {font-size: .86rem; color: var(--sm-muted); padding: .5rem .7rem; background: #f8fafc; border-radius: 10px;}
        @media (max-width: 760px) {
            .block-container {padding: 1rem;}
            .sm-hero h1 {font-size: 1.7rem;}
            .sm-stepper {grid-template-columns: 1fr; gap: 0;}
            .sm-step {padding: .4rem .25rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def api_get(path: str, timeout: float = 15.0) -> Any:
    with httpx.Client(timeout=timeout) as client:
        response = client.get(f"{API_URL}{path}")
        response.raise_for_status()
        return response.json()


def api_post(path: str, payload: dict[str, Any], timeout: float = 60.0) -> Any:
    with httpx.Client(timeout=timeout) as client:
        response = client.post(f"{API_URL}{path}", json=payload)
        response.raise_for_status()
        return response.json()


def friendly_error(error: Exception, action: str) -> str:
    if isinstance(error, httpx.TimeoutException):
        return f"{action} took longer than expected. Your progress is safe; please try again."
    if isinstance(error, httpx.HTTPStatusError):
        try:
            detail = error.response.json().get("detail")
        except Exception:
            detail = None
        if detail:
            return str(detail)
    return f"We couldn't {action.lower()}. Check that the local services are running and try again."


def reset_workflow() -> None:
    for key in (
        "resume_id",
        "resume_expires_at",
        "career_matches",
        "detected_skills",
        "analysis",
        "selected_occupation_id",
    ):
        st.session_state.pop(key, None)


def clear_downstream() -> None:
    st.session_state.career_matches = []
    st.session_state.analysis = None
    st.session_state.selected_occupation_id = None


def accept_resume(record: dict[str, Any]) -> None:
    st.session_state.resume_id = record["resume_id"]
    st.session_state.resume_expires_at = record.get("expires_at")
    st.session_state.detected_skills = record.get("skills", [])
    clear_downstream()


def render_stepper() -> None:
    current = 3 if st.session_state.analysis else 2 if st.session_state.resume_id else 1
    labels = ("Add résumé", "Explore matches", "Build roadmap")
    steps = []
    for index, label in enumerate(labels, start=1):
        state = "done" if index < current else "active" if index == current else ""
        marker = "✓" if index < current else str(index)
        steps.append(
            f'<div class="sm-step {state}"><span class="sm-step-number">{marker}</span><span>{label}</span></div>'
        )
    st.markdown('<div class="sm-stepper">' + "".join(steps) + "</div>", unsafe_allow_html=True)


def render_chips(values: list[str], kind: str = "") -> None:
    if not values:
        st.caption("None identified")
        return
    chips = "".join(f'<span class="sm-chip {kind}">{html.escape(value)}</span>' for value in values)
    st.markdown(chips, unsafe_allow_html=True)


def render_nodes() -> None:
    st.sidebar.markdown("### System status")
    try:
        nodes = api_get("/api/nodes", timeout=5.0)
        available = sum(1 for node in nodes if node.get("available"))
        st.sidebar.caption(f"{available} of {len(nodes)} local services available")
        with st.sidebar.expander("Service details"):
            for node in nodes:
                icon = "●" if node.get("available") else "○"
                st.write(f"{icon} {node['name']}")
    except Exception:
        st.sidebar.warning("Coordinator is unavailable")


def display_generation_mode(mode: str) -> str:
    if mode.startswith("ollama:"):
        return "AI explanation"
    if "fallback" in mode:
        return "Grounded summary"
    return "Generated report"


def build_analysis(
    occupation_id: str,
    maximum_courses: int = 4,
    preferred_level: str = "beginner",
    maximum_duration_hours: int = 40,
) -> None:
    st.session_state.selected_occupation_id = occupation_id
    st.session_state.analysis = api_post(
        "/api/analyses",
        {
            "resume_id": st.session_state.resume_id,
            "target_occupation_id": occupation_id,
            "maximum_courses": maximum_courses,
            "preferred_level": preferred_level,
            "maximum_duration_hours": maximum_duration_hours,
        },
        timeout=90.0,
    )


def skill_bar(item: dict[str, Any], state: str) -> None:
    confidence = float(item.get("user_confidence", 0.0))
    percent = max(0, min(round(confidence * 100), 100))
    st.markdown(
        f"""
        <div class="sm-skill">
          <div class="sm-skill-head">
            <span class="sm-skill-name">{html.escape(item['label'])}</span>
            <span class="sm-skill-value">{percent}% evidenced</span>
          </div>
          <div class="sm-track"><div class="sm-fill {state}" style="width:{max(percent, 4)}%"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_skill_group(title: str, description: str, items: list[dict[str, Any]], state: str) -> None:
    with st.container(border=True):
        st.markdown(f"#### {title}")
        st.caption(description)
        if not items:
            st.caption("No skills in this category.")
        for item in items[:8]:
            skill_bar(item, state)
            if state != "gap":
                with st.expander("Résumé evidence", expanded=False):
                    st.write(item.get("resume_evidence", "No explicit evidence found."))


def roadmap_markdown(analysis: dict[str, Any], hours_per_week: int) -> str:
    lines = [
        f"# SkillMesh roadmap: {analysis['target_occupation']}",
        "",
        f"- Career match: {analysis['match_score']:.1f}%",
        f"- Evidence coverage: {analysis['coverage_score']:.1f}%",
        "",
        analysis.get("summary", ""),
        "",
        "## Priority skill gaps",
    ]
    lines.extend(f"- {item['label']}" for item in analysis.get("gaps", []))
    lines.extend(["", "## Learning roadmap"])
    elapsed_hours = 0
    for index, course in enumerate(analysis.get("courses", []), start=1):
        metadata = course.get("metadata", {})
        duration = int(metadata.get("duration_hours", 0))
        start_week = elapsed_hours // hours_per_week + 1
        elapsed_hours += duration
        end_week = max(start_week, (elapsed_hours - 1) // hours_per_week + 1)
        week_label = f"Week {start_week}" if start_week == end_week else f"Weeks {start_week}–{end_week}"
        lines.append(f"{index}. **{course['title']}** — {week_label}, {duration} hours")
    lines.extend(["", "## Sources"])
    lines.extend(f"- {item['title']} ({item['evidence_id']})" for item in analysis.get("citations", []))
    return "\n".join(lines)


def render_roadmap(analysis: dict[str, Any], hours_per_week: int) -> None:
    courses = analysis.get("courses", [])
    st.markdown("### Your learning roadmap")
    st.caption(f"Sequenced at approximately {hours_per_week} study hours per week.")
    if not courses:
        st.info("No course recommendations were required or available.")
        return
    elapsed_hours = 0
    for course in courses:
        metadata = course.get("metadata", {})
        duration = int(metadata.get("duration_hours", 0))
        start_week = elapsed_hours // hours_per_week + 1
        elapsed_hours += duration
        end_week = max(start_week, (elapsed_hours - 1) // hours_per_week + 1)
        week_label = f"Week {start_week}" if start_week == end_week else f"Weeks {start_week}–{end_week}"
        addresses = [skill.replace("_", " ").title() for skill in course.get("addresses", [])]
        provider = metadata.get("provider", "Course catalog")
        level = str(metadata.get("level", "self-paced")).title()
        st.markdown(
            f"""
            <div class="sm-timeline">
              <div class="sm-week">{week_label}</div>
              <div class="sm-line"><span class="sm-dot"></span></div>
              <div class="sm-course">
                <div class="sm-course-title">{html.escape(course['title'])}</div>
                <div class="sm-course-meta">{html.escape(provider)} · {level} · {duration} hours</div>
                <div>{''.join(f'<span class="sm-chip">{html.escape(skill)}</span>' for skill in addresses)}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    weeks = (elapsed_hours - 1) // hours_per_week + 1
    st.caption(f"Estimated plan: {elapsed_hours} total hours across about {weeks} weeks.")


inject_styles()

default_resume = SAMPLE_RESUME.read_text(encoding="utf-8") if SAMPLE_RESUME.exists() else ""
defaults: dict[str, Any] = {
    "resume_id": None,
    "resume_expires_at": None,
    "career_matches": [],
    "detected_skills": [],
    "analysis": None,
    "selected_occupation_id": None,
    "resume_text": default_resume,
    "roadmap_hours_per_week": 6,
}
for state_key, default_value in defaults.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value

render_nodes()
if st.sidebar.button("Start over", use_container_width=True):
    reset_workflow()
    st.rerun()

st.markdown(
    """
    <div class="sm-hero">
      <div class="sm-eyebrow">Evidence-grounded career planning</div>
      <h1>Turn your experience into a clear next step.</h1>
      <p>Discover careers that fit your résumé, understand the skills standing between you and your target role, and build a focused learning plan.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
render_stepper()

if not st.session_state.resume_id:
    st.markdown('<div class="sm-kicker">Step 1 of 3</div>', unsafe_allow_html=True)
    st.header("Add your résumé")
    st.markdown('<p class="sm-section-copy">Upload a document or paste text to identify your current skills.</p>', unsafe_allow_html=True)
    upload_tab, text_tab = st.tabs(["Upload a file", "Paste résumé text"])

    with upload_tab:
        uploaded = st.file_uploader(
            "Choose a résumé",
            type=["pdf", "docx", "txt", "md"],
            help="Supported formats: PDF, DOCX, TXT, and Markdown.",
        )
        if uploaded:
            st.caption(f"Ready to analyze: {uploaded.name} · {len(uploaded.getvalue()) / 1024:.1f} KB")
        if st.button("Analyze uploaded résumé", type="primary", disabled=uploaded is None, use_container_width=True):
            try:
                with st.spinner("Reading your résumé and identifying skills..."):
                    with httpx.Client(timeout=30.0) as client:
                        response = client.post(
                            f"{API_URL}/api/resumes/upload",
                            files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                        )
                        response.raise_for_status()
                        accept_resume(response.json())
                st.rerun()
            except Exception as error:
                st.error(friendly_error(error, "Analyze your résumé"))

    with text_tab:
        st.text_area("Résumé text", height=260, key="resume_text", placeholder="Paste your résumé here...")
        if st.button("Analyze résumé text", type="primary", use_container_width=True):
            if len(st.session_state.resume_text.strip()) < 20:
                st.warning("Add at least a few sentences so SkillMesh can identify your experience.")
            else:
                try:
                    with st.spinner("Reading your résumé and identifying skills..."):
                        record = api_post("/api/resumes/text", {"text": st.session_state.resume_text})
                        accept_resume(record)
                    st.rerun()
                except Exception as error:
                    st.error(friendly_error(error, "Analyze your résumé"))

    st.markdown(
        '<div class="sm-privacy">🔒 Your résumé stays within your local SkillMesh services and expires automatically.</div>',
        unsafe_allow_html=True,
    )

elif not st.session_state.analysis:
    st.markdown('<div class="sm-kicker">Step 2 of 3</div>', unsafe_allow_html=True)
    st.header("Explore your career matches")
    skill_count = len(st.session_state.detected_skills)
    status_col, action_col = st.columns([3, 1])
    with status_col:
        st.success(f"Résumé ready · {skill_count} skills detected")
        if st.session_state.resume_expires_at:
            st.caption("Stored temporarily in the local résumé service.")
    with action_col:
        if st.button("Use another résumé", use_container_width=True):
            reset_workflow()
            st.rerun()

    with st.expander(f"Review {skill_count} detected skills", expanded=not st.session_state.career_matches):
        render_chips([skill["label"] for skill in st.session_state.detected_skills], "success")
        for skill in st.session_state.detected_skills:
            st.caption(f"{skill['label']} · {skill['confidence']:.0%} confidence — {skill['evidence']}")

    if not st.session_state.career_matches:
        st.markdown("#### Ready to see where your skills can take you?")
        st.caption("SkillMesh will compare your evidence with occupation requirements from the connected knowledge nodes.")
        if st.button("Find my best career matches", type="primary", use_container_width=True):
            try:
                with st.spinner("Comparing your skills with O*NET and ESCO evidence..."):
                    result = api_post(
                        "/api/career-matches",
                        {"resume_id": st.session_state.resume_id, "top_k": 5},
                        timeout=60.0,
                    )
                    st.session_state.career_matches = result["matches"]
                    st.session_state.detected_skills = result["detected_skills"]
                st.rerun()
            except Exception as error:
                st.error(friendly_error(error, "Rank career matches"))

    if st.session_state.career_matches:
        st.markdown("### Best-fit careers")
        st.caption("Select a role to customize and generate its complete skill-gap report.")
        for row_start in range(0, len(st.session_state.career_matches), 2):
            columns = st.columns(2)
            for column, match in zip(columns, st.session_state.career_matches[row_start : row_start + 2]):
                with column:
                    with st.container(border=True):
                        title_col, score_col = st.columns([3, 1])
                        title_col.markdown(f"#### {match['title']}")
                        score_col.metric("Match", f"{match['match_score']:.0f}%")
                        st.progress(min(match["match_score"] / 100, 1.0))
                        st.caption(f"Evidence coverage: {match['coverage_score']:.0f}%")
                        st.markdown("**Your strongest evidence**")
                        render_chips(match.get("top_strengths", []), "success")
                        st.markdown("**Skills to develop**")
                        render_chips(match.get("highest_gaps", []), "warning")
                        if st.button(
                            "Build this career roadmap",
                            key=f"choose-{match['occupation_id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            try:
                                with st.spinner(f"Building your {match['title']} roadmap..."):
                                    build_analysis(match["occupation_id"])
                                st.rerun()
                            except Exception as error:
                                st.error(friendly_error(error, "Build your skill-gap report"))

        options = {item["title"]: item["occupation_id"] for item in st.session_state.career_matches}
        selected_id = st.session_state.selected_occupation_id or next(iter(options.values()))
        selected_index = list(options.values()).index(selected_id) if selected_id in options.values() else 0
        with st.container(border=True):
            st.markdown("### Customize your roadmap")
            with st.form("analysis-settings"):
                target_title = st.selectbox("Target occupation", list(options), index=selected_index)
                control_columns = st.columns(4)
                max_courses = control_columns[0].slider("Maximum courses", 1, 8, 4)
                level = control_columns[1].selectbox("Preferred level", ["beginner", "intermediate"])
                max_duration = control_columns[2].slider("Hours per course", 4, 80, 40, step=2)
                weekly_hours = control_columns[3].slider("Study hours/week", 2, 20, st.session_state.roadmap_hours_per_week)
                submitted = st.form_submit_button("Build my skill-gap report", type="primary", use_container_width=True)
            if submitted:
                st.session_state.roadmap_hours_per_week = weekly_hours
                try:
                    with st.spinner("Retrieving evidence, calculating gaps, and generating your explanation..."):
                        build_analysis(options[target_title], max_courses, level, max_duration)
                    st.rerun()
                except Exception as error:
                    st.error(friendly_error(error, "Build your skill-gap report"))

analysis = st.session_state.analysis
if analysis:
    st.divider()
    st.markdown('<div class="sm-kicker">Step 3 of 3</div>', unsafe_allow_html=True)
    st.header(f"Your roadmap to {analysis['target_occupation']}")
    metric_columns = st.columns(3)
    metric_columns[0].metric("Career match", f"{analysis['match_score']:.1f}%")
    metric_columns[1].metric("Evidence coverage", f"{analysis['coverage_score']:.1f}%")
    metric_columns[2].metric("Report", display_generation_mode(analysis["generation_mode"]))
    st.progress(min(analysis["match_score"] / 100, 1.0))

    with st.container(border=True):
        st.markdown("### What this means")
        st.write(analysis["summary"])

    if analysis["degraded_sources"]:
        st.warning("Some knowledge sources were unavailable, so evidence coverage may be reduced.")

    st.markdown("### Your skill landscape")
    st.caption("Confidence reflects explicit evidence found in your résumé—not your full real-world ability.")
    skill_columns = st.columns(3)
    with skill_columns[0]:
        render_skill_group("Strong", "Clearly evidenced for this role", analysis["strengths"], "strong")
    with skill_columns[1]:
        render_skill_group("Developing", "Some evidence, with room to grow", analysis["partial_skills"], "developing")
    with skill_columns[2]:
        render_skill_group("Priority gaps", "Best opportunities to improve your fit", analysis["gaps"], "gap")

    render_roadmap(analysis, st.session_state.roadmap_hours_per_week)

    report = roadmap_markdown(analysis, st.session_state.roadmap_hours_per_week)
    download_col, matches_col, restart_col = st.columns(3)
    download_col.download_button(
        "Download roadmap",
        data=report,
        file_name=f"skillmesh-{analysis['target_occupation_id']}-roadmap.md",
        mime="text/markdown",
        use_container_width=True,
    )
    if matches_col.button("Back to career matches", use_container_width=True):
        st.session_state.analysis = None
        st.rerun()
    if restart_col.button("Use another résumé", use_container_width=True):
        reset_workflow()
        st.rerun()

    with st.expander(f"Evidence and technical details · {len(analysis['citations'])} sources"):
        st.markdown(f"**Generation mode:** `{analysis['generation_mode']}`")
        if analysis["warnings"]:
            st.markdown("**System notes**")
            for warning in analysis["warnings"]:
                st.caption("• " + warning)
        for citation in analysis["citations"]:
            st.markdown(f"**{citation['title']}** · `{citation['evidence_id']}`")
            st.write(citation["text"])
            if citation.get("source_url"):
                st.link_button("Open source", citation["source_url"])

st.divider()
st.caption("SkillMesh uses synthetic demonstration data. Import pinned official O*NET and ESCO exports before research evaluation.")
