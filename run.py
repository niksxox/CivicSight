
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

import os

import uvicorn


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))


def main() -> None:
    """Start the CivSight FastAPI application."""

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=os.getenv("ENVIRONMENT") == "development",
    )


if __name__ == "__main__":
    main()

