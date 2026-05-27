# AGENTS.md

Guidance for coding agents working in this repository.

## Repository shape

- `backend/` — FastAPI app, ingestion, retrieval, tests
- `frontend/` — Vue 3 + Vite UI
- `docker-compose.yml` — local full-stack runtime

## Canonical docs

- Use `README.md` for setup, run, and API usage.
- Keep this file focused on agent workflow expectations.

## Baseline commands

- Backend tests:
  ```bash
  cd backend && source .venv/bin/activate && pytest -q
  ```
- Frontend build:
  ```bash
  cd frontend && npm run build
  ```
- Compose validation:
  ```bash
  docker compose config
  ```

## Working expectations

- Prefer small, surgical changes aligned to existing patterns.
- Update docs when behavior or commands change.
- Do not revert unrelated local changes.
- Keep `README.md` as the single source of truth for developer setup.
