
"""
CivSight AI Infrastructure Intelligence
---------------------------------------

Simple application startup entry point.

Usage:
    python run.py

The FastAPI application itself is created in:
    app/main.py

Do not put AI/business logic in this file.
"""

from __future__ import annotations

import uvicorn


HOST = "127.0.0.1"
PORT = 8000


def main() -> None:
    """Start the CivSight FastAPI application."""

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
    )


if __name__ == "__main__":
    main()

