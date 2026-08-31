"""
Entrypoint. Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000

Docs auto-generated at /docs once running — that's the fastest way
to hand this to Chetan/Avinash to explore without reading code.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import projects, infrastructure, map as map_router, analytics, evidence

app = FastAPI(
    title="CivSight — Data & Analytics API",
    description=(
        "Data/analytics endpoints owned by the data pipeline layer. "
        "Application/business write-endpoints (assign officer, verify "
        "completion, etc.) live in a separate service."
    ),
    version="0.1.0",
)

# CORS: allow configured origins in production, wide-open for development
cors_origins = os.getenv("CORS_ORIGIN", "").split(",")
cors_origins = [o.strip() for o in cors_origins if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(projects.router)
app.include_router(infrastructure.router)
app.include_router(map_router.router)
app.include_router(analytics.router)
app.include_router(evidence.router)


@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "service": "civsight-data-backend"}


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "civsight-data-backend"}
