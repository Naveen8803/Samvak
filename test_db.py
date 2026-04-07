import mysql.connector
from config import Config

try:
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD
    )
    print("✅ MySQL Connection Successful")
    conn.close()
except Exception as e:
    print(f"❌ MySQL Connection Failed: {e}")
