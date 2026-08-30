"""
Applies db/schema.sql to whatever database DATABASE_URL points at.
Run once before the first ETL run:

    python scripts/init_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from app.config import settings

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


def main():
    schema_sql = SCHEMA_PATH.read_text()
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        conn.execute(text(schema_sql))
    print("Schema applied successfully.")


if __name__ == "__main__":
    main()
