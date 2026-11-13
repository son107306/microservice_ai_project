
from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 5000,
    overlap: int = 300
) -> List[str]:

    if not isinstance(text, str):
        raise TypeError("text phải là chuỗi string")

    if chunk_size <= 0:
        raise ValueError("chunk_size phải lớn hơn 0")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap phải nằm trong khoảng [0, chunk_size)")

    if not text.strip():
        return []

    chunks = []

    step = chunk_size - overlap
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start += step

    return chunks


if __name__ == "__main__":
    sample_text = "A" * 9397

    chunks = chunk_text(
        sample_text,
        chunk_size=5000,
        overlap=300
    )

    print("Tổng số chunk:", len(chunks))

    for i, chunk in enumerate(chunks, start=1):
        print(f"Chunk {i}: {len(chunk)} ký tự")
