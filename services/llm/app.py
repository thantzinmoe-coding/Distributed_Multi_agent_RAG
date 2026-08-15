from __future__ import annotations

import json
import os
from typing import Any

import httpx
from fastapi import FastAPI

from packages.contracts.api import GenerateRequest, GenerateResponse


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() in {"1", "true", "yes"}
app = FastAPI(title="SkillMesh grounded generation service", version="0.1.0")


def fallback_response(request: GenerateRequest, warning: str | None = None) -> GenerateResponse:
    strength_names = [item["label"] for item in request.strengths[:4]]
    gap_names = [item["label"] for item in request.gaps[:4]]
    summary_parts = [
        f"The evidence-grounded match for {request.target_occupation} is {request.match_score:.1f}%.",
        f"Current strengths include {', '.join(strength_names) if strength_names else 'no strongly evidenced target skills yet'}.",
        f"The highest-priority gaps are {', '.join(gap_names) if gap_names else 'none detected in the retrieved profile'}.",
    ]
    if request.courses:
        summary_parts.append("The proposed roadmap starts with " + ", ".join(course["title"] for course in request.courses[:3]) + ".")
    citations: list[str] = []
    for item in [*request.gaps[:4], *request.strengths[:3]]:
        citations.extend(item.get("evidence_ids", []))
    citations.extend(course["evidence_id"] for course in request.courses[:3])
    valid = {item.evidence_id for item in request.evidence}
    citations = list(dict.fromkeys(citation for citation in citations if citation in valid))
    warnings = []
    if request.degraded_sources:
        warnings.append("Unavailable sources: " + ", ".join(request.degraded_sources))
    if warning:
        warnings.append(warning)
    return GenerateResponse(summary=" ".join(summary_parts), citations=citations, mode="deterministic-fallback", warnings=warnings)


def parse_json_text(content: str) -> dict[str, Any]:
    value = content.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(value)


async def generate_with_ollama(request: GenerateRequest) -> GenerateResponse:
    allowed_ids = [record.evidence_id for record in request.evidence]
    system = (
        "You are SkillMesh. Use only the supplied evidence. Return JSON with keys "
        "summary (string), citations (array of evidence IDs), and warnings (array). "
        "Do not change numeric scores. Every factual requirement must use an allowed citation ID."
    )
    user = json.dumps({"analysis": request.model_dump(exclude={"evidence"}), "evidence": [item.model_dump() for item in request.evidence], "allowed_citation_ids": allowed_ids})
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "format": "json",
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "options": {"temperature": 0.1, "num_ctx": 6144},
            },
        )
        response.raise_for_status()
    parsed = parse_json_text(response.json()["message"]["content"])
    citations = list(dict.fromkeys(parsed.get("citations", [])))
    if not citations or any(citation not in allowed_ids for citation in citations):
        raise ValueError("The local model returned missing or invalid citations")
    return GenerateResponse(summary=parsed["summary"], citations=citations, mode=f"ollama:{OLLAMA_MODEL}", warnings=parsed.get("warnings", []))


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "node": "llm-service", "ollama_enabled": USE_OLLAMA, "model": OLLAMA_MODEL}


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    if not USE_OLLAMA:
        return fallback_response(request, "Local model is disabled; deterministic grounded narration was used.")
    try:
        return await generate_with_ollama(request)
    except Exception as error:
        return fallback_response(request, f"Local model unavailable or invalid; fallback used: {type(error).__name__}")
