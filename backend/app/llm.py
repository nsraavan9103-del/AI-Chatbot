from typing import Iterator

from app.config import Settings


def stream_answer(messages: list[dict], settings: Settings) -> Iterator[str]:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to .env and restart the backend.")

    from openai import OpenAI

    client = OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
    stream = client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        stream=True,
        temperature=0.2,
    )
    for chunk in stream:
        text = chunk.choices[0].delta.content
        if text:
            yield text
