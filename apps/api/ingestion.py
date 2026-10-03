import json
import uuid
from datetime import datetime, timedelta, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models import Document, IngestionJob
from rag import index_document

QUEUE = "document-ingestion"
MAX_ATTEMPTS = 3


def redis_client() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


async def enqueue(job_id: uuid.UUID) -> None:
    client = redis_client()
    try:
        await client.rpush(QUEUE, json.dumps({"job_id": str(job_id)}))
    finally:
        await client.aclose()


async def remove_queued_job(job_id: uuid.UUID) -> None:
    """Remove queued copies; the worker also safely ignores missing jobs."""
    client = redis_client()
    payload = json.dumps({"job_id": str(job_id)})
    try:
        await client.lrem(QUEUE, 0, payload)
    finally:
        await client.aclose()


async def create_or_reset_job(session: AsyncSession, document: Document) -> IngestionJob:
    job = await session.scalar(
        select(IngestionJob).where(IngestionJob.document_id == document.id)
    )
    if job is None:
        job = IngestionJob(document_id=document.id, tenant_id=document.tenant_id)
        session.add(job)
    else:
        job.status = "pending"
        job.error_message = None
        job.available_at = datetime.now(timezone.utc)
    document.status = "processing"
    await session.flush()
    return job


async def process_job(session: AsyncSession, job_id: uuid.UUID) -> None:
    job = await session.scalar(select(IngestionJob).where(IngestionJob.id == job_id))
    if job is None or job.status == "completed":
        return
    document = await session.scalar(select(Document).where(Document.id == job.document_id))
    if document is None:
        job.status = "failed"
        job.error_message = "Document no longer exists"
        await session.commit()
        return
    job.status = "running"
    job.attempts += 1
    await session.commit()
    try:
        await index_document(session, document)
        job.status = "completed"
        job.error_message = None
        await session.commit()
    except Exception as exc:
        await session.rollback()
        job = await session.scalar(select(IngestionJob).where(IngestionJob.id == job_id))
        document = await session.scalar(select(Document).where(Document.id == job.document_id))
        job.error_message = str(exc)[:1000]
        if job.attempts >= MAX_ATTEMPTS:
            job.status = "failed"
            document.status = "failed"
        else:
            job.status = "retry"
            job.available_at = datetime.now(timezone.utc) + timedelta(seconds=2 ** job.attempts)
        await session.commit()
        if job.status == "retry":
            await enqueue(job.id)
