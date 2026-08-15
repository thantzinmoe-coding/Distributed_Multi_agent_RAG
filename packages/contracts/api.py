from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = ""
    top_k: int = Field(default=8, ge=1, le=50)
    document_types: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)


class EvidenceRecord(BaseModel):
    evidence_id: str
    source: str
    title: str
    text: str
    score: float = 0.0
    source_url: str = ""
    source_version: str = "sample"
    license: str = ""
    document_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    node: str
    query: str
    results: list[EvidenceRecord]
    total_documents: int
    retrieval_mode: str = "hybrid-bm25-hashed-vector"


class TextResumeRequest(BaseModel):
    text: str = Field(min_length=20, max_length=100_000)


class ResumeSkill(BaseModel):
    skill_id: str
    label: str
    confidence: float
    evidence: str
    matched_alias: str


class ResumeRecord(BaseModel):
    resume_id: str
    text: str
    skills: list[ResumeSkill]
    created_at: str
    expires_at: str


class AnalysisRequest(BaseModel):
    resume_id: str
    target_occupation_id: str
    maximum_courses: int = Field(default=4, ge=1, le=8)
    preferred_level: str = "beginner"
    maximum_duration_hours: int = Field(default=40, ge=1, le=500)


class GenerateRequest(BaseModel):
    target_occupation: str
    match_score: float
    coverage_score: float
    strengths: list[dict[str, Any]]
    partial_skills: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    courses: list[dict[str, Any]]
    evidence: list[EvidenceRecord]
    degraded_sources: list[str] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    summary: str
    citations: list[str]
    mode: str
    warnings: list[str] = Field(default_factory=list)
