"""
Entrypoint. Run with:
    uvicorn app.main:app --reload

Docs auto-generated at /docs once running — that's the fastest way
to hand this to Chetan/Avinash to explore without reading code.
"""
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

# Wide open for hackathon demo purposes. Tighten this to the real
# frontend origin before anything resembling production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(infrastructure.router)
app.include_router(map_router.router)
app.include_router(analytics.router)
app.include_router(evidence.router)


@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "service": "civsight-data-backend"}
