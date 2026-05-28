import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock, patch


def _make_point(service="plex", time_range="x", log_text="line", levels=None, score=0.9):
    return MagicMock(
        score=score,
        payload={
            "service": service,
            "time_range": time_range,
            "log_text": log_text,
            "levels": levels or [],
        },
    )


@pytest.fixture
async def app_ctx():
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
            yield c, mock_qdrant


@respx.mock
async def test_health_all_services_ok(app_ctx):
    client, _ = app_ctx
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
async def test_health_degraded_when_embed_down(app_ctx):
    client, _ = app_ctx
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
async def test_search_returns_ok_status_with_sources(app_ctx):
    client, mock_qdrant = app_ctx
    mock_qdrant.query_points = AsyncMock(
        return_value=MagicMock(points=[_make_point()])
    )
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
    assert body["answer_status"] == "ok"
    assert len(body["sources"]) == 1
    assert body["sources"][0]["service"] == "plex"
    assert "score" in body["sources"][0]


@respx.mock
async def test_search_returns_no_results_status_when_empty(app_ctx):
    client, mock_qdrant = app_ctx
    mock_qdrant.query_points = AsyncMock(return_value=MagicMock(points=[]))
    embed_route = respx.post("http://localhost:8080/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})
    )
    generate_route = respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "should not be called"})
    )
    resp = await client.post("/search", json={"query": "no matches"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer_status"] == "no_results"
    assert body["answer"] is None
    assert body["sources"] == []
    assert embed_route.called
    assert not generate_route.called


@respx.mock
async def test_search_returns_llm_unavailable_when_generate_fails(app_ctx):
    client, mock_qdrant = app_ctx
    mock_qdrant.query_points = AsyncMock(
        return_value=MagicMock(points=[_make_point(levels=["error"])])
    )
    respx.post("http://localhost:8080/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})
    )
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(503)
    )
    resp = await client.post("/search", json={"query": "errors?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer_status"] == "llm_unavailable"
    assert body["answer"] is None
    assert len(body["sources"]) == 1


@respx.mock
async def test_search_returns_503_when_embed_fails(app_ctx):
    client, _ = app_ctx
    respx.post("http://localhost:8080/v1/embeddings").mock(
        return_value=httpx.Response(503)
    )
    resp = await client.post("/search", json={"query": "any errors?"})
    assert resp.status_code == 503
    assert "Embedding service unavailable" in resp.json()["detail"]


def _scroll_point(service, levels, time_range="2024-05-27 21:00–21:05 UTC"):
    return MagicMock(
        payload={
            "service": service,
            "time_range": time_range,
            "start_time": 1716843600.0,
            "levels": levels,
        }
    )


@respx.mock
async def test_meta_query_routes_to_aggregation(app_ctx):
    client, mock_qdrant = app_ctx
    mock_qdrant.scroll = AsyncMock(
        return_value=(
            [_scroll_point("plex", ["error"]), _scroll_point("sonarr", ["info"])],
            None,
        )
    )
    embed_route = respx.post("http://localhost:8080/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"embedding": [0.1]}]})
    )
    generate_route = respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "plex has the most errors."})
    )
    resp = await client.post(
        "/search", json={"query": "which container has the most errors?"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer_status"] == "ok"
    assert body["answer"] == "plex has the most errors."
    assert body["sources"] == []
    # aggregation path: no embedding call, scroll used not query_points
    assert not embed_route.called
    assert mock_qdrant.scroll.called
    assert not mock_qdrant.query_points.called
    # the deterministic stats reach the LLM prompt
    import json

    prompt = json.loads(generate_route.calls[0].request.content)["prompt"]
    assert "Distinct containers with errors: 1" in prompt


@respx.mock
async def test_meta_query_no_results(app_ctx):
    client, mock_qdrant = app_ctx
    mock_qdrant.scroll = AsyncMock(return_value=([], None))
    generate_route = respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "nope"})
    )
    resp = await client.post("/search", json={"query": "how many containers have errors?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer_status"] == "no_results"
    assert body["answer"] is None
    assert not generate_route.called


@respx.mock
async def test_content_query_uses_semantic_path(app_ctx):
    client, mock_qdrant = app_ctx
    mock_qdrant.scroll = AsyncMock(return_value=([], None))
    mock_qdrant.query_points = AsyncMock(
        return_value=MagicMock(points=[_make_point()])
    )
    respx.post("http://localhost:8080/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})
    )
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "Plex buffered."})
    )
    resp = await client.post("/search", json={"query": "did plex have buffering issues?"})
    assert resp.status_code == 200
    assert mock_qdrant.query_points.called
    assert not mock_qdrant.scroll.called


def test_is_meta_query_classification():
    from app.main import _is_meta_query

    assert _is_meta_query("which container has the most errors")
    assert _is_meta_query("how many containers have errors")
    assert _is_meta_query("count the errors per service")
    assert _is_meta_query("list all containers")
    assert not _is_meta_query("did plex have buffering issues?")
    assert not _is_meta_query("any errors in sonarr?")
