import json
import logging
import os
import re
import pika
import mysql.connector
import hashlib
from dotenv import load_dotenv
from openai import OpenAI

from config import (
    MQ_HOST,
    MQ_RAW_QUEUE,
    MQ_PROCESSED_QUEUE,
    ROOT_CATEGORIES,
    DB_HOST,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
    DB_PORT,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
ai_model = os.getenv("AI_MODEL", "gpt-4o")

db_config = {
    'host': DB_HOST,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME,
    'port': DB_PORT,
    'charset': 'utf8mb4',
}

PROMPT_TEMPLATE = """
次のWebページ内容を日本語で要約し、root_categories から該当するものを複数選んだ上で、
それぞれの root ラベルに対応するサブカテゴリー名の配列を推測してください。
出力は JSON のみとし、以下の形式に従ってください。

root_categories = {roots}

# 出力フォーマット
{{
  "summary": "...",
  "labels": [{{"root": "...", "sub": ["...", "..."]}}]
}}

[入力]
タイトル:{title}
本文:{text}
"""


def analyze_action(data: dict) -> dict:
    """Analyze page text using OpenAI API with DB caching."""
    title = data.get("title", "")
    text = data.get("text", "")[:1000]
    url = data.get("url", "")
    url_hash = hashlib.sha256(url.encode()).hexdigest()

    # check cache
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT summary, labels FROM pages WHERE url_hash=%s",
            (url_hash,),
        )
        row = cursor.fetchone()
        if row and row.get("summary"):
            logger.info("Cache hit for %s", url)
            labels = json.loads(row["labels"] or "[]")
            return {"summary": row["summary"], "labels": labels}
    except mysql.connector.Error as err:
        logger.error("MySQL error: %s", err)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    prompt = PROMPT_TEMPLATE.format(title=title, text=text, roots=ROOT_CATEGORIES)
    logger.info("Requesting summary from OpenAI for %s", url)
    logger.debug("Prompt: %s", prompt)
    try:
        response = client.chat.completions.create(
            model=ai_model,
            messages=[{"role": "user", "content": prompt}],
        )
        logger.info("OpenAI API response: %s", response)
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\s*', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\s*```$', '', content)
            content = content.strip()
        result = json.loads(content)
    except Exception as exc:
        logger.error(f"OpenAI API error: {exc}")
        result = {"summary": text[:200], "labels": []}

    # store result in cache
    logger.info("Caching result for %s", url)
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pages (url, url_hash, title, summary, labels)
            VALUES (%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE title=VALUES(title), summary=VALUES(summary), labels=VALUES(labels)
            """,
            (
                url,
                url_hash,
                title,
                result.get("summary"),
                json.dumps(result.get("labels", []), ensure_ascii=False),
            ),
        )
        conn.commit()
    except mysql.connector.Error as err:
        logger.error("MySQL error: %s", err)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return result


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
