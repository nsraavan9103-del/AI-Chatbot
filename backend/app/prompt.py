from app.retrieval import Hit

SYSTEM_PROMPT = (
    "You answer questions using only the context from the user's uploaded documents. "
    "Cite the sources you use with bracketed numbers such as [1]. "
    "If the context does not contain the answer, reply exactly: "
    "I don't know based on the uploaded documents."
)


def build_messages(question: str, hits: list[Hit]) -> list[dict[str, str]]:
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
        {"role": "user", "content": user},
    ]
