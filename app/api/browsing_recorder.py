import json
import logging
import mysql.connector
from typing import Dict, Any, Optional
import hashlib
from datetime import datetime
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowsingRecorder:
    """Receive browsing data from Chrome extension and store it in MySQL."""

    def __init__(self):
        self.config = {
            'host': DB_HOST,
            'user': DB_USER,
            'password': DB_PASSWORD,
            'database': DB_NAME,
            'port': DB_PORT,
            'charset': 'utf8mb4'
        }

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Convert ISO8601 string to naive datetime for MySQL."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            return None

    def insert_action(self, data: Dict[str, Any]) -> Optional[str]:
        """Insert browsing action data into pages and page_visits tables.

        Returns the summary text found in or stored for the page so that
        callers can continue processing even when this worker skips
        generating a new summary.
        """
        conn = None
        cursor = None
        summary = data.get('summary')
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()

            keywords = data.get('keywords')
            if isinstance(keywords, list):
                keywords = ','.join(keywords)

            scroll_depth = data.get('scroll_depth')
            if scroll_depth is None:
                scroll_depth = data.get('scrollDepth')
            try:
                scroll_depth = float(scroll_depth) if scroll_depth is not None else None
            except (ValueError, TypeError):
                scroll_depth = None

            url = data.get('url') or ''
            url_hash = hashlib.sha256(url.encode()).hexdigest()

            # check or insert page cache
            cursor.execute("SELECT id, summary FROM pages WHERE url_hash=%s", (url_hash,))
            row = cursor.fetchone()
            if row:
                logger.debug("Page cache hit for %s", url)
                page_id = row[0]
                if not summary:
                    summary = row[1]
            else:
                cursor.execute(
                    """
                    INSERT INTO pages (url, url_hash, title, summary, labels, keywords, search_query)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        url,
                        url_hash,
                        data.get('title'),
                        data.get('summary'),
                        json.dumps(data.get('labels', []), ensure_ascii=False),
                        keywords,
                        data.get('search_query'),
                    ),
                )
                page_id = cursor.lastrowid
                logger.debug("Inserted new page record for %s", url)

            # map categories to page
            labels = data.get('labels', [])
            for label in labels:
                root_name = label.get('root')
                subs = label.get('sub') or label.get('subs') or []
                if isinstance(subs, str):
                    subs = [subs]
                if not root_name:
                    continue
                cursor.execute(
                    "SELECT id FROM root_categories WHERE name=%s",
                    (root_name,),
                )
                root_row = cursor.fetchone()
                if not root_row:
                    continue
                root_id = root_row[0]
                for sub_name in subs:
                    if not sub_name:
                        continue
                    cursor.execute(
                        "SELECT id FROM sub_categories WHERE root_id=%s AND name=%s",
                        (root_id, sub_name),
                    )
                    sub_row = cursor.fetchone()
                    if sub_row:
                        sub_id = sub_row[0]
                    else:
                        cursor.execute(
                            "INSERT INTO sub_categories(root_id, name) VALUES (%s,%s)",
                            (root_id, sub_name),
                        )
                        sub_id = cursor.lastrowid
                    cursor.execute(
                        "INSERT IGNORE INTO page_categories(page_id, sub_id) VALUES (%s,%s)",
                        (page_id, sub_id),
                    )

            # insert user visit record
            cursor.execute(
                """
                INSERT INTO page_visits (page_id, user_id, session_id, scroll_depth, visit_start, visit_end)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (
                    page_id,
                    data.get('user_id'),
                    data.get('session_id'),
                    scroll_depth,
                    self._parse_datetime(data.get('visit_start')),
                    self._parse_datetime(data.get('visit_end')),
                ),
            )

            conn.commit()
            logger.info("Inserted page visit")
        except mysql.connector.Error as err:
            logger.error("MySQL Error: %s", err)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return summary
