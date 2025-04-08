"""
Hisaab API — Read-only JSON API for 8-scheme government transparency data.

Run:
    uvicorn api.main:app --reload
    # Then visit http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import district, freshness, nl_query, schemes

app = FastAPI(
    title="Hisaab API",
    description="Public accountability data for 8 Indian government welfare schemes",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(schemes.router, prefix="/api/v1", tags=["schemes"])
app.include_router(district.router, prefix="/api/v1", tags=["district"])
app.include_router(freshness.router, prefix="/api/v1", tags=["freshness"])
app.include_router(nl_query.router, prefix="/api/v1", tags=["query"])


@app.get("/")
def root():
    return {
        "name": "Hisaab API",
        "version": "0.1.0",
        "docs": "/docs",
        "schemes": 8,
        "endpoints": [
            "/api/v1/schemes",
            "/api/v1/district/{name}",
            "/api/v1/scheme/{scheme}",
            "/api/v1/brief/{district}",
            "/api/v1/red-flags",
            "/api/v1/data-quality",
            "/api/v1/freshness",
            "/api/v1/query",
        ],
    }
