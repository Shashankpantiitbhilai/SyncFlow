"""
Main entry point for workers.
"""
import asyncio
import logging
from typing import List

from .base_worker import BaseWorker
from .inbound_sync import InboundSyncWorker
from .outbound_sync import OutboundSyncWorker

logger = logging.getLogger(__name__)

async def run_workers():
    """Run all background workers."""
    workers: List[BaseWorker] = [
        InboundSyncWorker(),
        OutboundSyncWorker(),
    ]
    
    tasks = []
    for worker in workers:
        tasks.append(asyncio.create_task(worker.start()))
    
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Error running workers: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_workers())
