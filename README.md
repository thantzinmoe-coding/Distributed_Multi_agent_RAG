# SkillMesh

SkillMesh is a local, hybrid distributed RAG system for career recommendation and evidence-grounded skill-gap analysis. Independent Docker services own O*NET-style, ESCO-style, course, and private résumé data; a coordinator retrieves from them concurrently, calculates matches deterministically, and asks one shared generation service to explain the result with validated citations.

The repository starts with a small **synthetic demo corpus** so it runs immediately. It also includes adapters for pinned official O*NET and ESCO exports. Do not report evaluation results from the synthetic corpus as if it were official data.

## Architecture

```text
Streamlit UI
    |
Coordinator API
    |-- private résumé service
    |-- O*NET retrieval service
    |-- ESCO retrieval service
    |-- course retrieval service
    `-- grounded generation service --> optional Ollama/Qwen
```

The retrieval services use a dependency-free hybrid index: BM25 lexical ranking, deterministic hashed-vector ranking, and reciprocal-rank fusion. This keeps the demo small and offline-capable. A neural embedding backend can replace it later without changing service contracts.

## Implemented phases

### Phase 1 — Reproducible data core

- Canonical skill catalog and aliases
- Five synthetic occupation profiles
- Independent O*NET-style and ESCO-style corpora
- Sixteen learning resources
- Dataset manifests and explicit synthetic-data warnings
- Official-export conversion scripts

### Phase 2 — RAG and matching core

- Metadata-aware hybrid retrieval
- Reciprocal-rank fusion
- Résumé skill extraction with evidence spans
- Cross-source skill requirement fusion
- Deterministic career-match scoring
- Gap-priority calculation
- Greedy course set-cover ranking

### Phase 3 — Distributed services

- Independent FastAPI services and indexes
- Concurrent HTTP federation
- Health checks and timeouts
- Partial-failure handling
- Source-availability coverage score
- Private, expiring résumé store

### Phase 4 — Grounded generation

- Shared generation gateway
- Optional local Ollama/Qwen integration
- Structured generation request
- Citation allow-list validation
- Deterministic grounded fallback if the LLM is disabled or invalid

### Phase 5 — Interface and deployment

- Streamlit résumé, matching, gap, roadmap, and citation screens
- Docker Compose deployment
- Node-health display
- PDF, DOCX, TXT, and Markdown upload
- Healthy and degraded-mode smoke test

### Phase 6 — Verification

- Core unit tests
- Python compilation check
- Compose validation
- End-to-end API smoke script
- Live retrieval-node failure test

## Quick start

Choose one startup mode.

### Model-free mode

```powershell
docker compose up --build -d
```

This starts the complete application with deterministic grounded narration and does not download an LLM.

### Local Qwen mode

Create `.env` from `.env.example` and set:

```env
USE_OLLAMA=true
OLLAMA_MODEL=qwen3:4b
RESUME_TTL_MINUTES=60
SERVICE_TIMEOUT_SECONDS=5
```

For the first startup, run only these two commands:

```powershell
docker compose --profile local-llm up --build -d
docker compose exec ollama ollama pull qwen3:4b
```

The first command starts the entire project, including Ollama. A separate `docker compose up`, `docker compose restart llm-service`, or `docker compose ps` command is not required.

For later starts, run:

```powershell
docker compose --profile local-llm up -d
```

Open:

- UI: <http://localhost:8501>
- Coordinator API docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

Run the complete API smoke flow:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke.ps1
```

Stop model-free mode:

```powershell
docker compose down
```

Stop local Qwen mode:

```powershell
docker compose --profile local-llm down
```

The generation gateway validates that returned citation IDs exist in the retrieved evidence. If the model is unavailable or returns invalid citations, the system automatically uses deterministic narration.

## Demo script

1. Open the UI and use the bundled Alex Morgan résumé.
2. Process the résumé and inspect detected evidence.
3. Rank occupations; Backend Developer should rank highly.
4. Generate its skill-gap report and learning roadmap.
5. Stop one source node:

   ```powershell
   docker compose stop esco-service
   ```

6. Generate the report again. The result continues with reduced source coverage and a degraded warning.
7. Restore the node:

   ```powershell
   docker compose start esco-service
   ```

## Public API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/resumes/text` | Create an expiring résumé from text |
| `POST` | `/api/resumes/upload` | Upload PDF, DOCX, TXT, or Markdown |
| `DELETE` | `/api/resumes/{id}` | Delete private résumé data |
| `GET` | `/api/occupations` | Search federated occupations |
| `POST` | `/api/career-matches` | Rank occupations for a résumé |
| `POST` | `/api/analyses` | Generate a full gap report |
| `GET` | `/api/nodes` | Inspect distributed-node health |

Every retrieval node implements the same internal contract:

```http
POST /search
GET  /health
GET  /manifest
```

## Scoring

For required skills `i`:

```text
match = 100 * sum(required_importance_i * resume_evidence_confidence_i)
              / sum(required_importance_i)

gap_priority_i = required_importance_i * (1 - resume_evidence_confidence_i)
```

The LLM never calculates or changes these values. It only explains the retrieved and calculated result.

## Import official O*NET data

Download and extract a pinned O*NET database release. Then run, adapting filenames to the export:

```powershell
python scripts\ingest_onet.py `
  --occupation-data "data\raw\onet\Occupation Data.txt" `
  --skills "data\raw\onet\Skills.txt" `
  --tasks "data\raw\onet\Task Statements.txt" `
  --version "pinned-release" `
  --output "data\processed\onet_documents.json"
```

The adapter preserves source identifiers. Its automatic label slugs are **not** a reviewed O*NET/ESCO crosswalk. Review the selected occupations and skills before evaluation.

Point `DATA_PATH` for `onet-service` in `compose.yaml` to the processed file, then rebuild.

## Import official ESCO data

Download a pinned ESCO CSV release containing occupation, skill, and occupation-skill relationship files:

```powershell
python scripts\ingest_esco.py `
  --occupations "data\raw\esco\occupations_en.csv" `
  --skills "data\raw\esco\skills_en.csv" `
  --relations "data\raw\esco\occupationSkillRelations_en.csv" `
  --version "pinned-release" `
  --output "data\processed\esco_documents.json"
```

Review mappings, update the canonical skill catalog, point `esco-service` at the processed file, and rebuild.

## Tests

Core tests require only Python's standard library:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q packages services apps scripts
docker compose config --quiet
```

After starting Docker:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke.ps1
```

## Suggested evaluation dataset

Create 20–30 fictional résumés with manually labelled:

- Explicit skills
- Expected top occupations
- Expected priority gaps
- Suitable learning resources

Measure:

- Skill extraction precision, recall, and F1
- Retrieval Recall@5 and Recall@10
- Occupation NDCG@5
- Gap precision and recall
- Citation validity and coverage
- Healthy versus single-node-failure latency
- Peak RAM and VRAM

Compare O*NET only, ESCO only, and federated O*NET + ESCO.

## Privacy and safety

- Résumés remain local and expire after 60 minutes by default.
- Complete résumé text is not logged by application code.
- Upload size defaults to 5 MB.
- LLM citations are restricted to retrieved evidence IDs.
- Results are career guidance, not hiring decisions.
- Verify source licenses and attribution requirements for every imported release.

## Current limitations

- Bundled data is synthetic and intentionally small.
- Skill normalization is dictionary-based; full source imports require crosswalk review.
- The default vector ranker is lightweight rather than a neural embedding model.
- Résumé proficiency is inferred only as evidence confidence, not years or expert level.
- The résumé store is in memory and is not intended for multi-host production deployment.
