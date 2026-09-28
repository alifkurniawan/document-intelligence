"""Long-running worker that publishes committed processing jobs."""

from __future__ import annotations

import asyncio
import logging
import signal

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.core.database import create_engine
from app.repositories.document import SqlAlchemyMetadataUnitOfWork
from app.workers.rabbitmq import OutboxDispatcher, RabbitMQPublisher

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    if settings.database_url is None or settings.rabbitmq_url is None:
        raise RuntimeError("DATABASE_URL and RABBITMQ_URL are required for the outbox worker")
    engine = create_engine(settings)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    publisher = RabbitMQPublisher(settings)
    dispatcher = OutboxDispatcher(
        unit_of_work_factory=lambda: SqlAlchemyMetadataUnitOfWork(session_factory),
        publisher=publisher,
    )
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop_event.set)
    try:
        await publisher.connect()
        while not stop_event.is_set():
            try:
                await dispatcher.dispatch_once()
            except Exception:
                logger.exception("outbox dispatch cycle failed")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=1.0)
            except TimeoutError:
                pass
    finally:
        await publisher.close()
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
