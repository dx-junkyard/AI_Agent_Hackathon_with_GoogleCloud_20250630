import mysql.connector
from mysql.connector import errorcode
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

    def create_user(self, line_user_id=None):
        import uuid
        user_id = str(uuid.uuid4())
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (id, line_user_id) VALUES (%s,%s)",
                (user_id, line_user_id),
            )
            conn.commit()
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_DUP_ENTRY:
                cursor.execute(
                    "SELECT id FROM users WHERE line_user_id=%s",
                    (line_user_id,),
                )
                row = cursor.fetchone()
                user_id = row[0] if row else user_id
            else:
                print(f"[✗] MySQL Error: {err}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return user_id

    def insert_message(self, user_id, role, message):
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()

            query = """
                INSERT INTO user_messages (user_id, role, message)
                VALUES (%s, %s, %s)
            """
            values = (user_id, role, message)
            cursor.execute(query, values)
            conn.commit()

            print(f"[✓] Inserted user_messages for user_id={user_id} role={role}")

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
                SELECT user_id, role, message
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

