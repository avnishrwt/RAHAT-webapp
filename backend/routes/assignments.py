"""Optimizer runs and the assignments it produces."""
from fastapi import APIRouter
from sqlmodel import select

from backend.allocation import run_optimizer
from backend.db import SessionDep
from shared.schemas import Assignment, AssignmentStatus

router = APIRouter(tags=["assignments"])


@router.post("/optimize")
def optimize_now(session: SessionDep) -> list[Assignment]:
    """Recommend teams for all open incidents. Nothing is dispatched until approved."""
    return run_optimizer(session)


@router.get("/assignments")
def list_assignments(session: SessionDep, status: AssignmentStatus | None = None) -> list[Assignment]:
    query = select(Assignment)
    if status is not None:
        query = query.where(Assignment.status == status)
    return session.exec(query).all()
