import mysql.connector
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

class DBClient:
    def __init__(self):
        self.config = {
            'host': DB_HOST,
            'user': DB_USER,
            'password': DB_PASSWORD,
            'database': DB_NAME,
            'port': DB_PORT,
            'charset': 'utf8mb4'
        }

    def insert_message(self, user_id, message):
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()

            query = """
                INSERT INTO user_messages (user_id, message)
                VALUES (%s, %s)
            """
            values = (user_id, message)
            cursor.execute(query, values)
            conn.commit()

            print(f"[✓] Inserted user_messages for user_id={user_id}")

        except mysql.connector.Error as err:
            print(f"[✗] MySQL Error: {err}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_user_messages(self, user_id, limit=10):
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT user_id, message
                FROM user_messages
                WHERE user_id = %s
                ORDER BY id DESC
                LIMIT %s
            """
            cursor.execute(query, (user_id, limit))
            messages = cursor.fetchall()
            return messages
        except mysql.connector.Error as err:
            print(f"[✗] MySQL Error: {err}")
            return []
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

