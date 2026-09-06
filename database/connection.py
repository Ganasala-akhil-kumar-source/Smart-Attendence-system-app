import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "smart_attendance.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """
    Creates and returns a thread-safe SQLite connection with foreign keys enabled
    and Row factory configured for dictionary-like column access.
    """
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

@contextmanager
def get_db_cursor(db_path: Path = DB_PATH):
    """
    Context manager that yields a cursor and automatically commits or rolls back
    on exception, ensuring transactions are cleanly closed.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def init_db(db_path: Path = DB_PATH, schema_path: Path = SCHEMA_PATH):
    """
    Initializes the database schema if tables do not exist,
    and provisions default admin user.
    """
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection(db_path)
    with conn:
        conn.executescript(schema_sql)
    conn.close()

    # Import CRUD here to avoid circular dependencies
    from database.crud import get_admin_by_username, create_admin
    if not get_admin_by_username("admin", db_path):
        create_admin("admin", "admin123", db_path)
        print("[Database] Default administrator provisioned: username='admin', password='admin123'")

if __name__ == "__main__":
    init_db()
    print(f"[Database] Successfully initialized database at {DB_PATH}")
