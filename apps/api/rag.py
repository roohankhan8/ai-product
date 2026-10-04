"""Small, deterministic baseline RAG implementation.

The baseline uses local hashed word vectors so it runs without an API key. Replace
the embedding and search seams with pgvector or a hosted service after evaluation.
"""

import re
import unicodedata
import uuid
from io import BytesIO
from hashlib import blake2b
from dataclasses import dataclass
from math import sqrt
from pathlib import PurePath

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from core.errors import APIError
from models import Document, DocumentChunk
from storage import path_for

VECTOR_SIZE = 256
WORD_RE = re.compile(r"[\w']+", re.UNICODE)
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "do", "does", "for", "from",
    "have", "how", "i", "in", "is", "it", "of", "on", "or", "the", "to", "what",
    "where", "which", "who", "with", "you", "your",
}


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


def parse_text(filename: str, content: bytes) -> str:
    suffix = PurePath(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        except (ImportError, OSError, ValueError, PdfReadError) as exc:
            raise APIError(422, "invalid_pdf", "PDF could not be read") from exc
        if not text.strip():
            raise APIError(422, "empty_pdf_text", "PDF does not contain extractable text")
    elif suffix in {".txt", ".md"}:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise APIError(422, "invalid_text_encoding", "Document must be valid UTF-8 text") from exc
    else:
        raise APIError(415, "unsupported_parser_format", "Only PDF, text, and Markdown parsing is supported")
    normalized = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in normalized.splitlines()).strip()


def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    if not text:
        return []
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = text.rfind("\n", start, end)
            if boundary > start + size // 2:
                end = boundary
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return [item for item in chunks if item]


def embed(text: str) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    for word in WORD_RE.findall(text.casefold()):
        digest = blake2b(word.encode("utf-8"), digest_size=4).digest()
        vector[int.from_bytes(digest, "big") % VECTOR_SIZE] += 1.0
    norm = sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def meaningful_terms(text: str) -> set[str]:
    return {
        word for word in WORD_RE.findall(text.casefold())
        if word not in STOP_WORDS and len(word) > 2
    }


async def index_document(session: AsyncSession, document: Document) -> int:
    text = parse_text(document.original_filename, path_for(document.storage_key).read_bytes())
    chunks = chunk_text(text)
    await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    for index, content in enumerate(chunks):
        session.add(DocumentChunk(
            tenant_id=document.tenant_id,
            document_id=document.id,
            chunk_index=index,
            content=content,
            source_metadata={"filename": document.original_filename, "chunk_index": index},
            embedding=embed(content),
        ))
    document.status = "ready"
    return len(chunks)


async def retrieve(session: AsyncSession, tenant_id: uuid.UUID, query: str, top_k: int = 5) -> list[RetrievedChunk]:
    query_vector = embed(query)
    rows = await session.scalars(select(DocumentChunk).where(DocumentChunk.tenant_id == tenant_id))
    scored = []
    query_terms = meaningful_terms(query)
    for chunk in rows:
        if not query_terms.intersection(meaningful_terms(chunk.content)):
            continue
        score = sum(a * b for a, b in zip(query_vector, chunk.embedding))
        if score >= 0.18:
            scored.append(RetrievedChunk(chunk, score))
    return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]
