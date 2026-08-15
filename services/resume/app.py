from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi import FastAPI, File, HTTPException, UploadFile
from pypdf import PdfReader

from packages.contracts.api import ResumeRecord, TextResumeRequest
from packages.core.skills import extract_skills, load_skill_catalog


SKILL_CATALOG_PATH = Path(os.getenv("SKILL_CATALOG_PATH", "/app/data/sample/canonical_skills.json"))
TTL_MINUTES = int(os.getenv("RESUME_TTL_MINUTES", "60"))
MAX_FILE_BYTES = int(os.getenv("MAX_RESUME_BYTES", str(5 * 1024 * 1024)))

catalog = load_skill_catalog(SKILL_CATALOG_PATH)
store: dict[str, ResumeRecord] = {}
app = FastAPI(title="SkillMesh private résumé service", version="0.1.0")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def purge_expired() -> None:
    now = utcnow()
    expired = [resume_id for resume_id, record in store.items() if datetime.fromisoformat(record.expires_at) <= now]
    for resume_id in expired:
        store.pop(resume_id, None)


def create_record(text: str) -> ResumeRecord:
    cleaned = "\n".join(line.strip() for line in text.replace("\x00", "").splitlines() if line.strip())
    if len(cleaned) < 20:
        raise HTTPException(status_code=422, detail="The résumé does not contain enough extractable text")
    created = utcnow()
    record = ResumeRecord(
        resume_id=str(uuid.uuid4()),
        text=cleaned,
        skills=extract_skills(cleaned, catalog),
        created_at=created.isoformat(),
        expires_at=(created + timedelta(minutes=TTL_MINUTES)).isoformat(),
    )
    store[record.resume_id] = record
    return record


def extract_upload(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            reader = PdfReader(BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if suffix == ".docx":
            document = Document(BytesIO(content))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        if suffix in {".txt", ".md"}:
            return content.decode("utf-8", errors="replace")
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"Unable to parse résumé: {error}") from error
    raise HTTPException(status_code=415, detail="Supported formats are PDF, DOCX, TXT, and Markdown")


@app.get("/health")
def health() -> dict:
    purge_expired()
    return {"status": "healthy", "node": "resume-service", "active_resumes": len(store)}


@app.post("/resumes/text", response_model=ResumeRecord)
def create_text_resume(request: TextResumeRequest) -> ResumeRecord:
    purge_expired()
    return create_record(request.text)


@app.post("/resumes/upload", response_model=ResumeRecord)
async def create_uploaded_resume(file: UploadFile = File(...)) -> ResumeRecord:
    purge_expired()
    content = await file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Résumé file is larger than the configured limit")
    return create_record(extract_upload(file.filename or "resume.txt", content))


@app.get("/resumes/{resume_id}", response_model=ResumeRecord)
def get_resume(resume_id: str) -> ResumeRecord:
    purge_expired()
    if resume_id not in store:
        raise HTTPException(status_code=404, detail="Résumé not found or expired")
    return store[resume_id]


@app.delete("/resumes/{resume_id}")
def delete_resume(resume_id: str) -> dict:
    removed = store.pop(resume_id, None)
    return {"deleted": removed is not None, "resume_id": resume_id}
