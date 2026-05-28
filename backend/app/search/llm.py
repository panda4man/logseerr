import httpx

_PROMPT_TEMPLATE = """\
You are a log analysis assistant. Answer the user's question based only on the log excerpts below.
Be concise and specific. Use markdown formatting: bold for key terms, code blocks for log lines or \
values, and bullet lists when listing multiple items. If the logs contain no relevant information, \
say so clearly.

Log excerpts:
{context}

Question: {question}
Answer:"""


async def generate_answer(
    ollama_url: str, model: str, query: str, sources: list[dict]
) -> str | None:
    context = "\n\n---\n\n".join(
        f"[{s['service']} · {s['time_range']}]\n{s['log_text']}" for s in sources
    )
    prompt = _PROMPT_TEMPLATE.format(context=context, question=query)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["response"].strip()
    except (httpx.HTTPError, KeyError):
        return None
