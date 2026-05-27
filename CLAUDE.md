# CLAUDE.md

Project instructions for Claude-based coding sessions in this repo.

## Start here

1. Read `README.md` for architecture, env vars, and run commands.
2. Validate local state before editing (`git status`, active branch).
3. Make focused edits and keep docs in sync with behavior.

## Commands

- Backend tests:
  ```bash
  cd backend && source .venv/bin/activate && pytest -q
  ```
- Frontend build:
  ```bash
  cd frontend && npm run build
  ```
- Docker compose config check:
  ```bash
  docker compose config
  ```

## Notes

- Node version is pinned in `.nvmrc` (`24`).
- Qdrant is mapped to host `6334` in `docker-compose.yml`.
- If `/search` returns `Embedding service unavailable`, check `EMBED_URL` and embed service health.
