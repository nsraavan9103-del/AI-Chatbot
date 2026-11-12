def chunk_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        remaining = para
        while remaining:
            separator = "\n\n" if current else ""
            capacity = size - len(current) - len(separator)
            if capacity <= 0:
                chunks.append(current)
                current = chunks[-1][-overlap:] if overlap else ""
                continue
            if len(remaining) <= capacity:
                current = current + separator + remaining
                remaining = ""
            else:
                current = current + separator + remaining[:capacity]
                remaining = remaining[capacity:]
                chunks.append(current)
                current = chunks[-1][-overlap:] if overlap else ""

    if current.strip():
        chunks.append(current)
    return [chunk for chunk in chunks if chunk.strip()]
