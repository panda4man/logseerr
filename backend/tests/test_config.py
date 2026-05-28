from app.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.loki_url == "http://localhost:3100"
    assert s.embed_url == "http://localhost:8080"
    assert s.embed_model == "nomic-embed-text"
    assert s.qdrant_url == "http://localhost:6333"
    assert s.ollama_url == "http://localhost:11434"
    assert s.ollama_model == "llama3"
    assert s.ingest_interval_minutes == 15
    assert s.collection_name == "logseerr"
    assert s.search_top_k == 10
    assert s.search_min_score == 0.0
    assert s.aggregate_max_chunks == 10000
    assert s.loki_page_limit == 5000
    assert s.loki_max_pages == 50


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("LOKI_URL", "http://loki:3100")
    monkeypatch.setenv("OLLAMA_MODEL", "mistral")
    s = Settings()
    assert s.loki_url == "http://loki:3100"
    assert s.ollama_model == "mistral"
