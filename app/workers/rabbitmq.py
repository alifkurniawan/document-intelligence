"""RabbitMQ adapter using aio-pika, kept behind the publisher port."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aio_pika

from app.core.config import Settings
from app.workers.contracts import MessagePublisher, ProcessingMessage

logger = logging.getLogger(__name__)


class RabbitMQPublisher(MessagePublisher):
    def __init__(self, settings: Settings) -> None:
        if settings.rabbitmq_url is None:
            raise ValueError("RABBITMQ_URL is required")
        self.settings = settings
        self._connection: Any = None
        self._channel: Any = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(
            self.settings.rabbitmq_url.get_secret_value()
        )
        self._channel = await self._connection.channel(publisher_confirms=True)
        await self._channel.set_qos(prefetch_count=self.settings.rabbitmq_prefetch_count)
        exchange = await self._channel.declare_exchange(
            self.settings.rabbitmq_exchange, aio_pika.ExchangeType.DIRECT, durable=True
        )
        queue = await self._channel.declare_queue(
            self.settings.rabbitmq_queue,
            durable=True,
            arguments={
                "x-dead-letter-exchange": self.settings.rabbitmq_dlq_exchange,
                "x-dead-letter-routing-key": self.settings.rabbitmq_routing_key,
            },
        )
        await queue.bind(exchange, routing_key=self.settings.rabbitmq_routing_key)
        dlx = await self._channel.declare_exchange(
            self.settings.rabbitmq_dlq_exchange, aio_pika.ExchangeType.DIRECT, durable=True
        )
        dlq = await self._channel.declare_queue(self.settings.rabbitmq_dlq_queue, durable=True)
        await dlq.bind(dlx, routing_key=self.settings.rabbitmq_routing_key)

    async def publish(self, message: ProcessingMessage, *, routing_key: str) -> None:
        if self._channel is None:
            await self.connect()
        exchange = await self._channel.get_exchange(self.settings.rabbitmq_exchange)
        await asyncio.wait_for(
            exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message.as_payload(), separators=(",", ":")).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    message_id=str(message.job_id),
                    correlation_id=message.correlation_id or str(message.job_id),
                ),
                routing_key=routing_key,
            ),
            timeout=self.settings.rabbitmq_publish_timeout_seconds,
        )
        logger.info("processing message published", extra={"job_id": str(message.job_id)})

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None


class OutboxDispatcher:
    """Publishes committed outbox rows and marks them only after broker confirm."""

    def __init__(self, *, unit_of_work_factory, publisher: MessagePublisher) -> None:
        self.unit_of_work_factory = unit_of_work_factory
        self.publisher = publisher

    async def dispatch_once(self, *, limit: int = 100) -> int:
        published = 0
        async with self.unit_of_work_factory() as unit_of_work:
            for row in await unit_of_work.outbox.pending(limit=limit):
                try:
                    await self.publisher.publish(
                        ProcessingMessage(
                            document_id=row.document_id,
                            job_id=row.job_id,
                            original_artifact_id=row.original_artifact_id,
                            attempt=row.attempts,
                        ),
                        routing_key=row.routing_key,
                    )
                except Exception:
                    await unit_of_work.outbox.mark_attempted(row.outbox_id)
                    logger.exception(
                        "outbox publication failed", extra={"outbox_id": str(row.outbox_id)}
                    )
                    continue
                await unit_of_work.outbox.mark_published(row.outbox_id)
                logger.info("outbox marked published", extra={"outbox_id": str(row.outbox_id)})
                published += 1
            await unit_of_work.commit()
        return published


__all__ = ["OutboxDispatcher", "RabbitMQPublisher"]
