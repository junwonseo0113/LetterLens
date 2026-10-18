from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.apply import router as apply_router
from app.auth import router as auth_router
from app.benefits import router as benefits_router
from app.db import init_db
from app.docs import router as letters_router
from app.keep import router as reminders_router


@asynccontextmanager
async def lifespan(app: FastAPI):
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
