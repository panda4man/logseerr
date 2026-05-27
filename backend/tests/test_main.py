import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
async def client():
    mock_qdrant = AsyncMock()
    mock_qdrant.query_points = AsyncMock(return_value=MagicMock(points=[]))
    mock_qdrant.get_collections = AsyncMock(return_value=MagicMock(collections=[]))

    mock_scheduler = MagicMock()
    mock_scheduler.add_job = MagicMock()
    mock_scheduler.start = MagicMock()
    mock_scheduler.shutdown = MagicMock()

    import app.main as main_module

    with patch.object(main_module, "qdrant", mock_qdrant), patch.object(
        main_module, "scheduler", mock_scheduler
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main_module.app),
            base_url="http://test",
        ) as c:
            yield c


@respx.mock
async def test_health_all_services_ok(client):
    respx.get("http://localhost:8080/api/tags").mock(
        return_value=httpx.Response(200, json={"models": []})
    )
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": []})
    )
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["qdrant"] == "ok"
    assert body["embed"] == "ok"
    assert body["llm"] == "ok"


@respx.mock
async def test_health_degraded_when_embed_down(client):
    respx.get("http://localhost:8080/api/tags").mock(
        return_value=httpx.Response(503)
    )
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": []})
    )
    resp = await client.get("/health")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["embed"] == "unavailable"
    assert body["llm"] == "ok"


@respx.mock
async def test_search_returns_answer_and_sources(client):
    respx.post("http://localhost:8080/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})
    )
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "No issues found."})
    )
    resp = await client.post("/search", json={"query": "did plex have any issues?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "No issues found."
    assert "sources" in body


@respx.mock
async def test_search_returns_503_when_embed_fails(client):
    respx.post("http://localhost:8080/v1/embeddings").mock(
        return_value=httpx.Response(503)
    )
    resp = await client.post("/search", json={"query": "any errors?"})
    assert resp.status_code == 503
    assert "Embedding service unavailable" in resp.json()["detail"]
