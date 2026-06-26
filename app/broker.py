import os
import uuid
import json
import asyncio
import logging
import aio_pika
from typing import Optional, Dict, Any

logger = logging.getLogger("uvicorn.error")

RABBITMQ_URL = os.getenv("RABBITMQ_URL") or os.getenv("AMQP_URL")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

class TicketAnalysisRPCClient:
    def __init__(self):
        self.connection: Optional[aio_pika.abc.AbstractConnection] = None
        self.channel: Optional[aio_pika.abc.AbstractChannel] = None
        self.callback_queue: Optional[aio_pika.abc.AbstractQueue] = None
        self.futures: Dict[str, asyncio.Future] = {}
        self.loop = None

    async def connect(self):
        """Establish connection to RabbitMQ."""
        if not RABBITMQ_URL and not RABBITMQ_HOST:
            logger.info("RabbitMQ is not configured. Set RABBITMQ_URL or RABBITMQ_HOST to enable RPC.")
            self.connection = None
            return

        self.loop = asyncio.get_running_loop()
        try:
            if RABBITMQ_URL:
                self.connection = await aio_pika.connect_robust(
                    RABBITMQ_URL,
                    timeout=2.0
                )
            else:
                self.connection = await aio_pika.connect_robust(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    login=RABBITMQ_USER,
                    password=RABBITMQ_PASS,
                    timeout=2.0
                )
            self.channel = await self.connection.channel()
            self.callback_queue = await self.channel.declare_queue(
                name="", exclusive=True
            )
            await self.callback_queue.consume(self.on_response, no_ack=True)
            logger.info("Connected to RabbitMQ RPC broker successfully.")
        except Exception as e:
            target = RABBITMQ_URL or f"{RABBITMQ_HOST}:{RABBITMQ_PORT}"
            logger.warning(f"RabbitMQ is unavailable at {target} ({type(e).__name__}). RPC is disabled.")
            self.connection = None

    async def on_response(self, message: aio_pika.abc.AbstractIncomingMessage):
        """Process incoming RPC responses."""
        corr_id = message.correlation_id
        if corr_id in self.futures:
            future = self.futures.pop(corr_id)
            if not future.done():
                future.set_result(message.body)

    async def call(self, payload: Dict[str, Any], timeout: float = 12.0) -> Dict[str, Any]:
        """Send RPC request to worker and wait for response."""
        if not self.connection or self.connection.is_closed:
            await self.connect()
        if not self.connection or self.connection.is_closed:
            raise RuntimeError("RabbitMQ broker not connected.")

        corr_id = str(uuid.uuid4())
        future = self.loop.create_future()
        self.futures[corr_id] = future

        try:
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    content_type="application/json",
                    correlation_id=corr_id,
                    reply_to=self.callback_queue.name,
                ),
                routing_key="ticket_analysis_queue",
            )
            response_bytes = await asyncio.wait_for(future, timeout=timeout)
            return json.loads(response_bytes.decode())
        except asyncio.TimeoutError:
            self.futures.pop(corr_id, None)
            logger.warning(f"RabbitMQ RPC call timed out after {timeout} seconds.")
            raise
        except Exception as e:
            self.futures.pop(corr_id, None)
            logger.error(f"Error during RabbitMQ RPC call: {e}")
            raise

    async def close(self):
        """Close connections."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed.")
