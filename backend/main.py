"""RAHAT backend. Run from the repo root:  uvicorn backend.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import create_db
from backend.routes import assignments, incidents, messages, teams


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()  # runs once at startup
    yield


app = FastAPI(title="RAHAT", lifespan=lifespan)

# Demo only: Manshi's React dev server runs on a different port.
# A real deployment lists the dashboard's exact origin here.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(messages.router)
app.include_router(incidents.router)
app.include_router(teams.router)
app.include_router(assignments.router)


@app.get("/health")
def health():
    return {"ok": True}
