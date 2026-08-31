import os
import subprocess
import sys
from pathlib import Path

import uvicorn


def apply_schema():
    """Apply the idempotent schema before starting the API.

    Render free web services do not support preDeployCommand, so schema setup
    happens at startup instead. schema.sql is designed to be safe to re-run.
    """
    script = Path(__file__).resolve().parent / "scripts" / "init_db.py"
    result = subprocess.run([sys.executable, str(script)], check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    apply_schema()
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT", "production") == "development",
    )
