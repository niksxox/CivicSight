
"""
CivSight AI Infrastructure Intelligence
---------------------------------------

FastAPI application entry point.

Responsibilities:
    - Create the FastAPI application.
    - Register API routers.
    - Configure API metadata.
    - Expose Swagger/OpenAPI documentation.

Business logic belongs in app/services/.
HTTP route definitions belong in app/api/routes.py.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router


# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------

APP_TITLE = "CivSight AI Infrastructure Intelligence"
APP_DESCRIPTION = (
    "AI service for infrastructure condition analysis, "
    "project progress assessment, priority scoring, "
    "issue extraction, and resolution verification."
)
APP_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """
    Create and configure the CivSight FastAPI application.

    Keeping application creation inside a factory makes the application
    easier to test and prevents import-time side effects.
    """

    application = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.include_router(router)

    return application


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = create_app()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
# This is an infrastructure-level health endpoint, not an additional
# AI-service endpoint. It is useful for confirming that FastAPI itself
# started successfully before testing the five mandatory AI endpoints.


@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
)
async def health_check() -> dict[str, str]:
    """
    Return a minimal service health response.
    """

    return {
        "status": "ok",
        "service": "civSight-ai",
    }


__all__ = [
    "app",
    "create_app",
]

