from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.docs import router as letters_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="LetterLens API", lifespan=lifespan)
app.include_router(letters_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
