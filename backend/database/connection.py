import os
import duckdb
from pathlib import Path

# Resolve the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "football_probability.duckdb"

def get_db_path() -> str:
    """Returns the path to the DuckDB database file."""
    return os.environ.get("FOOTBALL_DB_PATH", str(DEFAULT_DB_PATH))

def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Establishes a connection to the DuckDB database."""
    db_path = get_db_path()
    # Ensure directory exists if path is custom
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return duckdb.connect(db_path, read_only=read_only)

def init_db() -> None:
    """Initializes the database by running schema.sql if tables do not exist."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
        
    conn = get_connection(read_only=False)
    try:
        # Execute the schema SQL
        # DuckDB supports multiple statements in one execute call
        conn.execute(schema_sql)
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
