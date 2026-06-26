import os
import json
import asyncio
import logging
import aio_pika
from app.services.analyzer import run_analysis_pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("queue_worker")

RABBITMQ_URL = os.getenv("RABBITMQ_URL") or os.getenv("AMQP_URL")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

async def main():
    while True:
        if not RABBITMQ_URL and not RABBITMQ_HOST:
            logger.error("RabbitMQ is not configured. Set RABBITMQ_URL or RABBITMQ_HOST. Retrying in 30 seconds...")
            await asyncio.sleep(30)
            continue

        try:
            if RABBITMQ_URL:
                logger.info("Connecting to RabbitMQ using RABBITMQ_URL...")
                connection = await aio_pika.connect_robust(
                    RABBITMQ_URL,
                    timeout=5.0
                )
            else:
                logger.info(f"Connecting to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}...")
                connection = await aio_pika.connect_robust(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    login=RABBITMQ_USER,
                    password=RABBITMQ_PASS,
                    timeout=5.0
                )
            
            async with connection:
                channel = await connection.channel()
                # Prefetch 1 message to distribute load evenly
                await channel.set_qos(prefetch_count=1)
                
                queue = await channel.declare_queue("ticket_analysis_queue", durable=True)
                logger.info("Worker is ready and waiting for messages in ticket_analysis_queue.")
                
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        async with message.process():
                            try:
                                logger.info(f"Received ticket request. correlation_id: {message.correlation_id}")
                                payload = json.loads(message.body.decode())
                                
                                # Run the pipeline
                                response_data = run_analysis_pipeline(payload)
                                
                                # Publish the response back to the reply_to queue
                                if message.reply_to:
                                    await channel.default_exchange.publish(
                                        aio_pika.Message(
                                            body=json.dumps(response_data).encode(),
                                            content_type="application/json",
                                            correlation_id=message.correlation_id,
                                        ),
                                        routing_key=message.reply_to,
                                    )
                                    logger.info(f"Replied with status 200. correlation_id: {message.correlation_id}")
                                else:
                                    logger.warning("Message did not contain reply_to header.")
                            except Exception as e:
                                logger.error(f"Error processing message: {e}", exc_info=True)
                                # Publish error back to client
                                if message.reply_to:
                                    err_res = {"error": str(e), "ticket_id": payload.get("ticket_id") if 'payload' in locals() else None}
                                    await channel.default_exchange.publish(
                                        aio_pika.Message(
                                            body=json.dumps(err_res).encode(),
                                            content_type="application/json",
                                            correlation_id=message.correlation_id,
                                        ),
                                        routing_key=message.reply_to,
                                    )
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("Worker shutting down.")
            break
        except Exception as e:
            logger.error(f"RabbitMQ connection failed: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
