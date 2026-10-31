"""Team registry (PRD FR08)."""
from fastapi import APIRouter
from sqlmodel import select

from backend.db import SessionDep
from shared.schemas import Team

router = APIRouter(tags=["teams"])


@router.get("/teams")
def list_teams(session: SessionDep) -> list[Team]:
    return session.exec(select(Team).order_by(Team.id)).all()
