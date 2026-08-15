from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

from packages.contracts.api import SearchRequest, SearchResponse
from packages.core.retrieval import HybridIndex, load_documents


NODE_NAME = os.getenv("NODE_NAME", "retriever")
DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data/sample/onet_documents.json"))
MANIFEST_PATH = Path(os.getenv("MANIFEST_PATH", "/app/data/manifests/onet.json"))

if not DATA_PATH.exists():
    raise RuntimeError(f"Retrieval data not found: {DATA_PATH}")

documents = load_documents(DATA_PATH)
index = HybridIndex(documents)
app = FastAPI(title=f"SkillMesh {NODE_NAME}", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "node": NODE_NAME,
        "documents": len(documents),
        "data_path": str(DATA_PATH),
    }


@app.get("/manifest")
def manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    results = index.search(
        query=request.query,
        top_k=request.top_k,
        document_types=request.document_types,
        filters=request.filters,
    )
    return SearchResponse(
        node=NODE_NAME,
        query=request.query,
        results=results,
        total_documents=len(documents),
    )
