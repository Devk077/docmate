"""
DoqToq Groups — FastAPI Application

Entry point for the API layer that replaces the Streamlit frontend.

Run with:
    uvicorn api.main:app --reload --port 8000

Endpoints:
    /api/rooms         → rooms CRUD
    /api/rooms/{id}/documents  → document upload + indexing
    /api/rooms/{id}/chat       → SSE streaming chat
    /api/rooms/{id}/sessions   → session management
    /api/rooms/{id}/history    → chat history
    /docs              → interactive Swagger docs (auto-generated)
    /health            → health check
"""

import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s +0530 - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("api.main")

# ── Lifespan ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic."""
    logger.info("DoqToq API starting up...")

    # Verify DATABASE_URL is set
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL not set — DB operations will fail")
    else:
        logger.info(f"Database URL: {db_url[:40]}...")

    logger.info("DoqToq API ready — listening on port 8000")
    yield
    logger.info("DoqToq API shutting down")


# ── App ────────────────────────────────────────────────────────

app = FastAPI(
    title="DoqToq Groups API",
    description=(
        "Backend API for DoqToq Discussion Rooms. "
        "Upload documents, create rooms, and stream multi-speaker AI discussions."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────
# Allow the React dev server (port 5173) and any local origin.
# Adjust FRONTEND_URL in .env for production.

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────

from api.routes.rooms import router as rooms_router
from api.routes.documents import router as documents_router
from api.routes.chat import router as chat_router

app.include_router(rooms_router)
app.include_router(documents_router)
app.include_router(chat_router)


# ── Health check ───────────────────────────────────────────────

@app.get("/health", tags=["meta"], summary="Health check")
async def health():
    """Returns OK if the API is running."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/", tags=["meta"], include_in_schema=False)
async def root():
    return {
        "message": "DoqToq Groups API",
        "docs": "/docs",
        "health": "/health",
    }
