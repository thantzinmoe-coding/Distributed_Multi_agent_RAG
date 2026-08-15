from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from packages.contracts.api import AnalysisRequest, GenerateRequest, TextResumeRequest
from packages.core.matching import analyze_gap, merge_requirements, rank_courses


SERVICE_URLS = {
    "resume-service": os.getenv("RESUME_SERVICE_URL", "http://resume-service:8000"),
    "onet-service": os.getenv("ONET_SERVICE_URL", "http://onet-service:8000"),
    "esco-service": os.getenv("ESCO_SERVICE_URL", "http://esco-service:8000"),
    "course-service": os.getenv("COURSE_SERVICE_URL", "http://course-service:8000"),
    "llm-service": os.getenv("LLM_SERVICE_URL", "http://llm-service:8000"),
}
REQUEST_TIMEOUT = float(os.getenv("SERVICE_TIMEOUT_SECONDS", "5"))

app = FastAPI(title="SkillMesh federated coordinator", version="0.1.0")


class CareerMatchRequest(BaseModel):
    resume_id: str
    top_k: int = Field(default=5, ge=1, le=10)


async def get_json(url: str, timeout: float = REQUEST_TIMEOUT) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def post_json(url: str, payload: dict[str, Any], timeout: float = REQUEST_TIMEOUT) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def search_service(name: str, payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]], str | None]:
    try:
        response = await post_json(f"{SERVICE_URLS[name]}/search", payload)
        return name, response.get("results", []), None
    except Exception as error:
        return name, [], type(error).__name__


async def node_health(name: str, base_url: str) -> dict[str, Any]:
    try:
        result = await get_json(f"{base_url}/health", timeout=2.0)
        return {"name": name, "available": True, **result}
    except Exception as error:
        return {"name": name, "available": False, "status": "unavailable", "error": type(error).__name__}


async def all_health() -> list[dict[str, Any]]:
    return await asyncio.gather(*(node_health(name, url) for name, url in SERVICE_URLS.items()))


async def retrieve_occupation(occupation_id: str) -> tuple[list[dict[str, Any]], list[str]]:
    payload = {
        "query": occupation_id.replace("_", " "),
        "top_k": 50,
        "document_types": ["occupation", "skill_requirement"],
        "filters": {"canonical_occupation_id": occupation_id},
    }
    responses = await asyncio.gather(
        search_service("onet-service", payload),
        search_service("esco-service", payload),
    )
    evidence: list[dict[str, Any]] = []
    degraded: list[str] = []
    for name, results, error in responses:
        evidence.extend(results)
        if error:
            degraded.append(name)
    return evidence, degraded


def apply_source_availability(analysis: dict[str, Any], degraded: list[str]) -> None:
    unavailable_knowledge_nodes = {"onet-service", "esco-service"}.intersection(degraded)
    source_availability = 100.0 * (2 - len(unavailable_knowledge_nodes)) / 2
    analysis["coverage_score"] = round(min(analysis["coverage_score"], source_availability), 1)


@app.get("/health")
async def health() -> dict[str, Any]:
    statuses = await all_health()
    return {
        "status": "healthy" if any(item["available"] for item in statuses) else "degraded",
        "node": "coordinator",
        "services": statuses,
    }


@app.get("/api/nodes")
async def nodes() -> list[dict[str, Any]]:
    return await all_health()


@app.post("/api/resumes/text")
async def create_text_resume(request: TextResumeRequest) -> dict[str, Any]:
    try:
        return await post_json(f"{SERVICE_URLS['resume-service']}/resumes/text", request.model_dump())
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=error.response.status_code, detail=error.response.text) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Résumé service is unavailable") from error


@app.post("/api/resumes/upload")
async def create_uploaded_resume(file: UploadFile = File(...)) -> dict[str, Any]:
    content = await file.read()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{SERVICE_URLS['resume-service']}/resumes/upload",
                files={"file": (file.filename or "resume.txt", content, file.content_type or "application/octet-stream")},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=error.response.status_code, detail=error.response.text) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Résumé service is unavailable") from error


@app.delete("/api/resumes/{resume_id}")
async def delete_resume(resume_id: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.delete(f"{SERVICE_URLS['resume-service']}/resumes/{resume_id}")
            response.raise_for_status()
            return response.json()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Unable to delete résumé") from error


@app.get("/api/occupations")
async def occupations(query: str = Query(default="", max_length=100)) -> list[dict[str, Any]]:
    payload = {"query": query, "top_k": 50, "document_types": ["occupation"], "filters": {}}
    responses = await asyncio.gather(
        search_service("onet-service", payload),
        search_service("esco-service", payload),
    )
    merged: dict[str, dict[str, Any]] = {}
    for name, results, _ in responses:
        for result in results:
            occupation_id = result["metadata"].get("canonical_occupation_id")
            if not occupation_id:
                continue
            item = merged.setdefault(
                occupation_id,
                {
                    "id": occupation_id,
                    "title": result["metadata"].get("occupation_title", result["title"]),
                    "description": result["text"],
                    "score": 0.0,
                    "sources": [],
                },
            )
            item["score"] = max(item["score"], result.get("score", 0.0))
            item["sources"].append(name)
    return sorted(merged.values(), key=lambda item: (-item["score"], item["title"]))


@app.post("/api/career-matches")
async def career_matches(request: CareerMatchRequest) -> dict[str, Any]:
    try:
        resume = await get_json(f"{SERVICE_URLS['resume-service']}/resumes/{request.resume_id}")
    except Exception as error:
        raise HTTPException(status_code=404, detail="Résumé not found or expired") from error

    catalog = await occupations("")

    async def score_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
        evidence, degraded = await retrieve_occupation(item["id"])
        requirements = merge_requirements(evidence)
        if not requirements:
            return None
        analysis = analyze_gap(requirements, resume["skills"])
        apply_source_availability(analysis, degraded)
        return {
            "occupation_id": item["id"],
            "title": item["title"],
            "match_score": analysis["match_score"],
            "coverage_score": analysis["coverage_score"],
            "top_strengths": [value["label"] for value in analysis["strengths"][:3]],
            "highest_gaps": [value["label"] for value in analysis["gaps"][:3]],
            "degraded_sources": degraded,
        }

    results = await asyncio.gather(*(score_candidate(item) for item in catalog))
    ranked = sorted((item for item in results if item), key=lambda item: (-item["match_score"], item["title"]))
    return {"resume_id": request.resume_id, "matches": ranked[: request.top_k], "detected_skills": resume["skills"]}


@app.post("/api/analyses")
async def analyze(request: AnalysisRequest) -> dict[str, Any]:
    try:
        resume = await get_json(f"{SERVICE_URLS['resume-service']}/resumes/{request.resume_id}")
    except Exception as error:
        raise HTTPException(status_code=404, detail="Résumé not found or expired") from error

    evidence, degraded = await retrieve_occupation(request.target_occupation_id)
    requirements = merge_requirements(evidence)
    if not requirements:
        raise HTTPException(status_code=503, detail="No occupation evidence is available from O*NET or ESCO nodes")

    occupation_record = next((item for item in evidence if item["document_type"] == "occupation"), None)
    occupation_title = (
        occupation_record["metadata"].get("occupation_title")
        if occupation_record
        else request.target_occupation_id.replace("_", " ").title()
    )
    analysis = analyze_gap(requirements, resume["skills"])
    apply_source_availability(analysis, degraded)

    courses: list[dict[str, Any]] = []
    if analysis["gaps"]:
        course_query = " ".join(item["label"] for item in analysis["gaps"][:8])
        _, course_results, course_error = await search_service(
            "course-service",
            {"query": course_query, "top_k": 30, "document_types": ["course"], "filters": {}},
        )
        if course_error:
            degraded.append("course-service")
        else:
            courses = rank_courses(
                course_results,
                analysis["gaps"],
                request.maximum_courses,
                request.preferred_level,
                request.maximum_duration_hours,
            )

    evidence_by_id = {item["evidence_id"]: item for item in evidence}
    for course in courses:
        evidence_by_id[course["evidence_id"]] = course
    llm_payload = GenerateRequest(
        target_occupation=occupation_title,
        match_score=analysis["match_score"],
        coverage_score=analysis["coverage_score"],
        strengths=analysis["strengths"],
        partial_skills=analysis["partial_skills"],
        gaps=analysis["gaps"],
        courses=courses,
        evidence=list(evidence_by_id.values()),
        degraded_sources=sorted(set(degraded)),
    )
    try:
        generation = await post_json(f"{SERVICE_URLS['llm-service']}/generate", llm_payload.model_dump(), timeout=50.0)
    except Exception:
        generation = {
            "summary": f"The calculated match for {occupation_title} is {analysis['match_score']:.1f}%.",
            "citations": [item["evidence_id"] for item in evidence[:5]],
            "mode": "coordinator-fallback",
            "warnings": ["Generation service unavailable."],
        }

    valid_citations = [citation for citation in generation.get("citations", []) if citation in evidence_by_id]
    citation_details = [evidence_by_id[citation] for citation in valid_citations]
    return {
        "resume_id": request.resume_id,
        "target_occupation_id": request.target_occupation_id,
        "target_occupation": occupation_title,
        "match_score": analysis["match_score"],
        "coverage_score": analysis["coverage_score"],
        "detected_skills": resume["skills"],
        "strengths": analysis["strengths"],
        "partial_skills": analysis["partial_skills"],
        "gaps": analysis["gaps"],
        "courses": courses,
        "summary": generation.get("summary", ""),
        "generation_mode": generation.get("mode", "unknown"),
        "warnings": generation.get("warnings", []),
        "degraded_sources": sorted(set(degraded)),
        "citations": citation_details,
    }
