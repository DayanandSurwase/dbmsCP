import mysql.connector
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME


def get_connection(database=None):
    """
    Return a new MySQL connection.
    autocommit=False so callers can manage transactions explicitly.
    """
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database or DB_NAME,
        autocommit=False
    )


if __name__ == "__main__":
    print("Testing database connectivity...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE(), VERSION()")
        row = cursor.fetchone()
        print(f"  Connected to database : {row[0]}")
        print(f"  MySQL server version  : {row[1]}")
        cursor.close()
        conn.close()
        print("Connectivity test PASSED.")
    except Exception as e:
        print(f"Connectivity test FAILED: {e}")
