import sqlite3
from config import Config

def setup_database():
    print(f"Initializing database at: {Config.DB_PATH}")
    
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        cur = conn.cursor()
        
        # Create Users Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """)
        
        # Create Translations Table (History)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            source_type TEXT NOT NULL,
            input_text TEXT NOT NULL,
            output_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Database tables created successfully.")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")

if __name__ == "__main__":
    setup_database()
