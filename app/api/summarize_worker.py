import json
import logging
import pika

from app.api.page_analyzer import analyze_page
from config import MQ_HOST, MQ_RAW_QUEUE, MQ_PROCESSED_QUEUE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_action(data: dict) -> dict:
    """Analyze incoming page data and return summary and labels."""
    title = data.get("title", "")
    text = data.get("text", "")
    url = data.get("url", "")
    source_type = data.get("source_type", "web")
    return analyze_page(title=title, text=text, url=url, source_type=source_type)


def main() -> None:
    params = pika.ConnectionParameters(
        host=MQ_HOST,
        connection_attempts=5,
        retry_delay=5,
    )
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=MQ_RAW_QUEUE, durable=True)
    channel.queue_declare(queue=MQ_PROCESSED_QUEUE, durable=True)

    def callback(ch, method, properties, body):
        data = json.loads(body)
        analyzed = analyze_action(data)
        data.update(analyzed)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        publish_params = pika.ConnectionParameters(
            host=MQ_HOST,
            connection_attempts=5,
            retry_delay=5,
        )
        publish_connection = pika.BlockingConnection(publish_params)
        publish_channel = publish_connection.channel()
        publish_channel.queue_declare(queue=MQ_PROCESSED_QUEUE, durable=True)
        publish_channel.basic_publish(
            exchange="",
            routing_key=MQ_PROCESSED_QUEUE,
            body=json.dumps(data),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        publish_connection.close()
        logger.info("Processed action sent to next queue")

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=MQ_RAW_QUEUE, on_message_callback=callback)
    logger.info("Summarize worker started. Waiting for messages...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
