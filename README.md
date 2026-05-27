# logseerr

`logseerr` is a local log-search assistant: it ingests logs, stores embeddings in Qdrant, and answers natural-language questions through a FastAPI backend and Vue frontend.

## Stack

- **Backend:** FastAPI + APScheduler + Qdrant client (`backend/`)
- **Frontend:** Vue 3 + Vite + Tailwind (`frontend/`)
- **Infra:** Docker Compose (`docker-compose.yml`)

## Prerequisites

- Docker + Docker Compose
- Node.js 24 (`.nvmrc`)
- Python 3.12 (for local backend development)

## Quick start (Docker)

1. Copy env file:

```bash
cp .env.example .env
```

2. Edit `.env` with reachable service URLs:

- `LOKI_URL`
- `EMBED_URL` — Ollama embeddings instance (serves OpenAI-compatible `/v1/embeddings`)
- `OLLAMA_URL` — Ollama LLM instance (serves `/api/generate` for RAG)
- `VITE_API_BASE_URL`

> **Dual-Ollama setup:** The project uses two separate Ollama instances — one
> dedicated to embeddings (port `11435`) and one for LLM generation (port
> `11434`). This keeps embedding workloads isolated from inference. Both run on
> the same unraid host (`192.168.50.46`) but could be split across machines.

3. Build and run:

```bash
docker compose build
docker compose up -d
```

4. Verify:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"did plex have any issues in the last 24 hours?"}'
```

Notes:
- Frontend is served at `http://localhost`
- Backend is served at `http://localhost:8000`
- Qdrant is exposed on host port `6334` (`6334 -> 6333` in container)

## Local development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run tests:

```bash
cd backend
source .venv/bin/activate
pytest -q
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Build:

```bash
cd frontend
npm run build
```

## API

- `GET /health` → checks connectivity to Qdrant, embed server, and LLM:

```json
{ "status": "ok", "qdrant": "ok", "embed": "ok", "llm": "ok" }
```

Returns `503` with `"status": "degraded"` if any service is unreachable.
- `POST /search` with JSON body:

```json
{ "query": "did plex have any issues in the last 24 hours?" }
```

Response:

```json
{
  "answer": "string | null",
  "sources": []
}
```

If embeddings are unavailable, `/search` returns `503` with `Embedding service unavailable`.
