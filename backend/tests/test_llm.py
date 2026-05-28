import json
import respx
import httpx
from app.search.llm import generate_aggregate_answer, generate_answer

OLLAMA_URL = "http://ollama:11434"
MODEL = "llama3"
SOURCES = [
    {
        "service": "plex",
        "time_range": "2024-05-27 21:00–21:05 UTC",
        "log_text": "buffering error: stream stalled at 720p",
    }
]


@respx.mock
async def test_generate_answer_returns_string():
    respx.post(f"{OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "Plex had a buffering error."})
    )
    result = await generate_answer(OLLAMA_URL, MODEL, "did plex have issues?", SOURCES)
    assert result == "Plex had a buffering error."


@respx.mock
async def test_generate_answer_includes_sources_and_query_in_prompt():
    route = respx.post(f"{OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "answer"})
    )
    await generate_answer(OLLAMA_URL, MODEL, "any plex issues?", SOURCES)
    body = json.loads(route.calls[0].request.content)
    assert "buffering error" in body["prompt"]
    assert "any plex issues?" in body["prompt"]
    assert body["stream"] is False


@respx.mock
async def test_generate_answer_returns_none_on_http_error():
    respx.post(f"{OLLAMA_URL}/api/generate").mock(return_value=httpx.Response(503))
    result = await generate_answer(OLLAMA_URL, MODEL, "question", SOURCES)
    assert result is None


async def test_generate_answer_returns_none_on_connect_error():
    result = await generate_answer(
        "http://unreachable-host-xyz:11434", MODEL, "question", SOURCES
    )
    assert result is None


STATS = "Distinct containers: 2\nDistinct containers with errors: 1\n- plex: 3 / 5"


@respx.mock
async def test_generate_aggregate_answer_includes_stats_and_query_in_prompt():
    route = respx.post(f"{OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "plex has the most errors."})
    )
    result = await generate_aggregate_answer(
        OLLAMA_URL, MODEL, "which container has the most errors?", STATS
    )
    assert result == "plex has the most errors."
    body = json.loads(route.calls[0].request.content)
    assert "Distinct containers with errors: 1" in body["prompt"]
    assert "which container has the most errors?" in body["prompt"]
    assert body["stream"] is False


@respx.mock
async def test_generate_aggregate_answer_returns_none_on_http_error():
    respx.post(f"{OLLAMA_URL}/api/generate").mock(return_value=httpx.Response(503))
    result = await generate_aggregate_answer(OLLAMA_URL, MODEL, "how many?", STATS)
    assert result is None
