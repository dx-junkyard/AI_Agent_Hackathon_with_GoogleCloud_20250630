import json
import logging
import os
import re
import hashlib
import mysql.connector
from dotenv import load_dotenv
from openai import OpenAI

from config import (
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

PROMPT_TEMPLATE = """次のWebページ内容を日本語で要約し、root_categories から該当するものを複数選んだ上で、\
それぞれの root ラベルに対応するサブカテゴリー名の配列を推測してください。\n出力は JSON のみとし、以下の形式に従ってください。\n\nroot_categories = {roots}\n\n# 出力フォーマット\n{{\n  \"summary\": \"...\",\n  \"labels\": [{{\"root\": \"...\", \"sub\": [\"...\", \"...\"]}}]\n}}\n\n[入力]\nタイトル:{title}\n本文:{text}"""


def analyze_page(title: str, text: str, url: str = "", source_type: str = "web") -> dict:
    """Analyze given text and store summary and labels in the DB."""
    text = text[:1000]
    if url:
        url_hash = hashlib.sha256(url.encode()).hexdigest()
    else:
        url_hash = hashlib.sha256(text.encode()).hexdigest()

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
            logger.info("Cache hit for %s", url if url else "text")
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
    logger.info("Requesting summary from OpenAI for %s", url if url else "text")
    logger.debug("Prompt: %s", prompt)
    try:
        response = client.chat.completions.create(
            model=ai_model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\s*', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\s*```$', '', content)
            content = content.strip()
        result = json.loads(content)
    except Exception as exc:
        logger.error(f"OpenAI API error: {exc}")
        result = {"summary": text[:200], "labels": []}

    logger.info("Caching result for %s", url if url else "text")
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pages (url, url_hash, title, summary, labels, source_type)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE title=VALUES(title), summary=VALUES(summary), labels=VALUES(labels), source_type=VALUES(source_type)
            """,
            (
                url,
                url_hash,
                title,
                result.get("summary"),
                json.dumps(result.get("labels", []), ensure_ascii=False),
                source_type,
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
