import json
import pika
import logging
from config import MQ_HOST

logger = logging.getLogger(__name__)


def _connect() -> pika.BlockingConnection:
    """Create a connection to RabbitMQ with retries."""
    params = pika.ConnectionParameters(
        host=MQ_HOST,
        connection_attempts=5,
        retry_delay=5,
    )
    logger.debug("Connecting to RabbitMQ at %s", MQ_HOST)
    return pika.BlockingConnection(params)


def publish_message(queue: str, data: dict) -> None:
    """Publish a JSON message to the specified RabbitMQ queue."""
    connection = None
    try:
        connection = _connect()
        channel = connection.channel()
        channel.queue_declare(queue=queue, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(data),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        logger.info("Message queued on %s: %s", queue, data)
    except Exception as exc:
        logger.error("Failed to publish message: %s", exc)
    finally:
        if connection:
            connection.close()
