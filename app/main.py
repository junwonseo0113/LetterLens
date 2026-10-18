from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import settings
from app.apply import router as apply_router
from app.auth import router as auth_router
from app.benefits import router as benefits_router
from app.db import init_db
from app.docs import router as letters_router
from app.keep import router as reminders_router


# Show real-OCI failures (see app.trace.call_with_fallback) in the server log.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Outside DEMO_MODE, refuse to start with demo shortcuts or missing settings.
    settings.assert_production_ready()
    init_db()
    yield


app = FastAPI(title="LetterLens API", lifespan=lifespan)

# Demo-only: wide open so the Vite dev server (any localhost port) can call
# the API. Tighten this to specific origins before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(letters_router)
app.include_router(reminders_router)
app.include_router(benefits_router)
app.include_router(auth_router)
app.include_router(apply_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
