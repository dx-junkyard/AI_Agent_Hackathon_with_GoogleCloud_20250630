import json
import logging
import requests
from datetime import datetime
import pika

from app.api.browsing_recorder import BrowsingRecorder
from config import MQ_HOST, MQ_PROCESSED_QUEUE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    recorder = BrowsingRecorder()
    params = pika.ConnectionParameters(
        host=MQ_HOST,
        connection_attempts=5,
        retry_delay=5,
    )
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=MQ_PROCESSED_QUEUE, durable=True)

    API_ENDPOINT = "http://api:8000/send-notification"
    TIME_THRESHOLD = 30  # seconds
    SCROLL_THRESHOLD = 0.3

    def _parse_time(value: str) -> datetime:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return datetime.utcnow()

    def callback(ch, method, properties, body):
        data = json.loads(body)
        logger.debug("Received data: %s", data)
        stored_summary = recorder.insert_action(data)
        if stored_summary and not data.get("summary"):
            data["summary"] = stored_summary

        scroll = data.get("scroll_depth") or data.get("scrollDepth") or 0
        try:
            scroll = float(scroll)
        except (ValueError, TypeError):
            scroll = 0

        start = data.get("visit_start")
        end = data.get("visit_end")
        if start and end:
            start_dt = _parse_time(start)
            end_dt = _parse_time(end)
            duration = (end_dt - start_dt).total_seconds()
        else:
            duration = 0
        logger.debug("Visit duration=%s scroll=%s", duration, scroll)

        if duration >= TIME_THRESHOLD and scroll >= SCROLL_THRESHOLD:
            title = data.get("title") or data.get("url")
            summary = data.get("summary") or ""
            message = f"\u3055\u304d\u307b\u3069\u3054\u89b3\u306b\u306a\u3063\u305f\u300c{title}\u300d\u304c\u6c17\u306b\u306a\u3063\u305f\u3088\u3046\u3067\u3059\u306d\u3002{summary}\u306b\u3064\u3044\u3066\u610f\u898b\u3092\u304d\u304b\u305b\u3066\u304f\u3060\u3055\u3044\u3002"
            logger.info("Interest detected: duration=%s scroll=%s", duration, scroll)
            logger.info("Sending message to Chrome extension: %s", message)
            try:
                resp = requests.post(API_ENDPOINT, json={"message": message}, timeout=5)
                logger.info("Notification response status: %s", resp.status_code)
            except Exception as exc:
                logger.error("Failed to send notification: %s", exc)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=MQ_PROCESSED_QUEUE, on_message_callback=callback)
    logger.info("DB worker started. Waiting for processed messages...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
