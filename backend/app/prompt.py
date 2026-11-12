import re
from typing import Sequence

from app.retrieval import Hit

SYSTEM_PROMPT = (
    "You are a helpful assistant inside a document research tool. "
    "The user may have uploaded documents; relevant excerpts are given as Context.\n\n"
    "Rules:\n"
    "1. If the Context answers the question, use it and cite the excerpt number in "
    "brackets, like [1].\n"
    "2. Cite only the numbers that appear in the Context. Never invent a citation.\n"
    "3. If the Context is empty or does not cover the question, answer from your own "
    "general knowledge and cite nothing.\n"
    "4. Never claim a document says something it does not.\n"
    "5. Answer in plain prose. No markdown headings, no bullet symbols."
)

CITATION = re.compile(r"\[(\d+)\]")


def build_messages(
    question: str,
    hits: list[Hit],
    history: Sequence[dict[str, str]] = (),
) -> list[dict[str, str]]:
    if hits:
        context = "\n\n".join(
            f"[{rank}] ({hit.filename}, part {hit.idx})\n{hit.text}"
            for rank, hit in enumerate(hits, start=1)
        )
    else:
        context = "No context available."
    user = f"Question: {question}\n\nContext:\n{context}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user},
    ]


def derive_mode(answer: str, source_count: int) -> str:
    if source_count <= 0:
        return "general"
    cited = {int(number) for number in CITATION.findall(answer)}
    if any(1 <= number <= source_count for number in cited):
        return "documents"
    return "general"
