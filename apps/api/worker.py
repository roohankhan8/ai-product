"""Run with: python -m worker (from apps/api)."""

import asyncio
import json
import logging
import uuid

from redis.asyncio import Redis

from database import session_factory
from ingestion import QUEUE, process_job, redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run() -> None:
    client: Redis = redis_client()
    try:
        logger.info("document worker started")
        while True:
            item = await client.blpop(QUEUE, timeout=5)
            if not item:
                continue
            payload = json.loads(item[1])
            async with session_factory() as session:
                await process_job(session, uuid.UUID(payload["job_id"]))
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(run())
