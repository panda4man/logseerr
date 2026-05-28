QDRANT_URL ?= http://localhost:6334
BACKEND_URL ?= http://localhost:8000
COLLECTION ?= logseerr

.PHONY: up down qdrant-clear ingest

up:
	docker compose up -d

down:
	docker compose down

qdrant-clear:
	@echo "Deleting Qdrant collection '$(COLLECTION)' at $(QDRANT_URL)..."
	@curl -sS -X DELETE "$(QDRANT_URL)/collections/$(COLLECTION)" && echo ""

ingest:
	@echo "Triggering ingestion at $(BACKEND_URL)/ingest..."
	@curl -sS -X POST "$(BACKEND_URL)/ingest" && echo ""
