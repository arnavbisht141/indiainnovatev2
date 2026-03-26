"""
Nagar Mirror — FastAPI application entry point.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_driver, close_driver
from app.routers import infrastructure, seed_status, complaints, trust

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: open DB on startup, close on shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_driver()
    logger.info("🚀  Nagar Mirror API started")
    yield
    await close_driver()
    logger.info("Nagar Mirror API shutdown complete.")


# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Nagar Mirror API",
    description="City infrastructure graph + citizen complaint management",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the PWA and dashboard origins
raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
origins = [o.strip() for o in raw_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(infrastructure.router, prefix="/api")
app.include_router(seed_status.router, prefix="/api")
app.include_router(complaints.router, prefix="/api")
app.include_router(trust.router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "nagar-mirror-api"}

# ---------------------------------------------------------------------------
# Serve Frontend Static Build
# ---------------------------------------------------------------------------
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

if os.path.isdir(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fallback to index.html for SPA routing
        return FileResponse(os.path.join(static_dir, "index.html"))
