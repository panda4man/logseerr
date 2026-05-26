# logseerr — Natural Language Log Search Interface

**Date:** 2026-05-26  
**Status:** Approved

---

## Problem Statement

A homelab Unraid box runs Loki aggregating logs from 5 servers and their containers. Querying logs currently requires writing LogQL. The goal is a simple natural-language interface where you can ask questions like "did Plex have any issues streaming in the last 24 hours?" and receive a plain-English answer backed by the actual matching log excerpts.

---

## Architecture Overview

```
Vue SPA (Vite + Tailwind)
        │  POST /search
        ▼
FastAPI (Python)
    ├── Search endpoint
    │       └── Embed Server → Qdrant → Ollama → response
    └── Ingestion worker (APScheduler, every 15 min)
                └── Loki HTTP API → chunk → Embed Server → Qdrant upsert

External services (all HTTP, pre-existing):
  - Loki HTTP API
  - Embed Server (REST API, RTX 3060 / GTX 1660 Super)
  - Qdrant (Docker on Unraid — new)
  - Ollama (existing)
```

The FastAPI app hosts both the search API and the background ingestion scheduler in a single process. All external service calls are HTTP — no native GPU drivers or Python ML libraries required beyond `httpx` and `qdrant-client`.

> **Implementation note:** The embed server's exact request/response format (OpenAI-compatible vs. custom) should be confirmed before writing `embedder.py`. The `embedder.py` module isolates this contract so only one file needs updating if the format differs.

---

## Ingestion Pipeline

**Trigger:** APScheduler fires every 15 minutes inside the FastAPI process.

**Per run:**
1. Read last-ingested timestamp from a SQLite state file (one row per Loki stream label)
2. Query Loki's HTTP API: `GET /loki/api/v1/query_range` for all streams in the time window
3. Group log lines into **5-minute time-window chunks per service/job label** (e.g., all Plex logs 14:00–14:05 become one chunk)
4. For each chunk: `POST` raw log text to embed server → receive embedding vector
5. Upsert into Qdrant with payload: `{ service, start_time, end_time, log_text }`

**Deduplication:** SQLite state file tracks the last successfully processed timestamp per Loki stream. On restart, ingestion resumes from the last checkpoint.

**Qdrant collection:** Single collection named `logseerr`. The `service` label is stored as a payload field to allow filtered queries without managing multiple collections.

---

## Search / Query Pipeline

**Endpoint:** `POST /search`  
**Request body:** `{ "query": "did plex have any issues streaming in the last 24 hours?" }`

**Steps:**
1. Embed the query text via the embed server
2. Search Qdrant for top-10 most similar chunks. If the query contains a time reference ("last 24 hours", "last week"), apply a basic heuristic time filter on `start_time` payload field.
3. Build a RAG prompt: inject top-10 log chunks as context, ask Ollama to answer the original question
4. Call Ollama (`POST /api/generate`) with the configured model
5. Return response:
```json
{
  "answer": "Plex had 3 buffering errors between 9:00–9:15pm on May 25th.",
  "sources": [
    { "service": "plex", "time_range": "2026-05-25 21:00–21:05", "log_text": "..." },
    ...
  ]
}
```

---

## Frontend (Vue SPA)

**Stack:** Vue 3 + Vite + Tailwind CSS. Single page, no router.

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  🔍 logseerr                                     │
│  ┌─────────────────────────────────────────┐    │
│  │ Ask anything about your logs...        │ [Go]│
│  └─────────────────────────────────────────┘    │
│                                                   │
│  ┌── Answer ──────────────────────────────────┐  │
│  │ "Plex had 3 buffering errors on 5/25..."   │  │
│  └────────────────────────────────────────────┘  │
│                                                   │
│  ▼ Sources (3 log chunks)                        │
│    [plex · 2026-05-25 21:00–21:05] ▶             │
│    [plex · 2026-05-25 21:05–21:10] ▶             │
│    [network · 2026-05-25 20:58–21:03] ▶          │
└─────────────────────────────────────────────────┘
```

**Components:**
- `App.vue` — root, holds state (query, answer, sources, loading)
- `SearchBar.vue` — text input + submit button, emits `search` event
- `AnswerCard.vue` — displays the LLM-generated answer
- `SourceList.vue` — renders list of source chunks
- `SourceChunk.vue` — collapsible: shows service + time range header, expands to raw log text
- `api.js` — single `search(query)` fetch wrapper using `VITE_API_BASE_URL` env var

**Config:** `.env.example` documents `VITE_API_BASE_URL=http://localhost:8000` so the frontend can target any host.

---

## Error Handling

- **Embed server unavailable:** Return HTTP 503 with message "Embedding service unavailable"
- **Qdrant unavailable:** Return HTTP 503 with message "Vector search unavailable"
- **Ollama unavailable / timeout:** Return the source chunks with `answer: null` and a UI message "Could not generate summary — showing raw results"
- **Loki unavailable during ingestion:** Log the error, skip the run, retry on next schedule tick
- **Ingestion failure mid-run:** State file is only updated after successful upsert, so partial runs re-process on next tick

---

## Project Structure

```
logseerr/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app + APScheduler setup
│   │   ├── config.py         # Settings via env vars (Loki, embed, Qdrant, Ollama URLs)
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── loki.py       # Loki HTTP client (query_range)
│   │   │   ├── chunker.py    # 5-min time-window chunking per service
│   │   │   ├── embedder.py   # HTTP client for embed server
│   │   │   └── indexer.py    # Qdrant upsert logic
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   ├── retriever.py  # Qdrant similarity search + time filter
│   │   │   └── llm.py        # Ollama /api/generate client
│   │   └── state.py          # SQLite ingestion checkpoint (aiosqlite)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── components/
│   │   │   ├── SearchBar.vue
│   │   │   ├── AnswerCard.vue
│   │   │   ├── SourceList.vue
│   │   │   └── SourceChunk.vue
│   │   └── api.js
│   ├── .env.example
│   ├── index.html
│   ├── vite.config.js
│   └── Dockerfile
└── docker-compose.yml        # Qdrant + backend + frontend (nginx)
```

---

## Deployment

A single `docker-compose.yml` on Unraid runs:
- `qdrant` — official Qdrant Docker image with persistent volume
- `backend` — FastAPI app (Python 3.12 slim), reads config from env vars
- `frontend` — Vite-built Vue app served by nginx on port 80

Backend config (via env vars or `.env` file):
```
LOKI_URL=http://<loki-host>:3100
EMBED_URL=http://<embed-server>:<port>
QDRANT_URL=http://qdrant:6333
OLLAMA_URL=http://<ollama-host>:11434
OLLAMA_MODEL=llama3
INGEST_INTERVAL_MINUTES=15
```

The Loki, embed server, and Ollama services remain external — the compose stack only manages Qdrant + the new app services.

---

## Out of Scope

- Authentication (internal network only)
- Multi-user sessions or query history
- Streaming LLM responses (response is returned when complete)
- Manual log ingestion triggers
- Multiple Qdrant collections (single collection with service as payload filter)
