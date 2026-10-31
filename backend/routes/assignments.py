"""Optimizer runs and the operator's decisions on what it recommends (PRD FR09, FR10)."""
from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from backend.allocation import active_assignments, eta_min, refresh_team_status, run_optimizer
from backend.audit import audit, snapshot
from backend.db import SessionDep, get_or_404
from backend.optimizer import pair_cost
from shared.schemas import (ApproveIn, Assignment, AssignmentStatus, Incident, IncidentStatus,
                            RejectIn, Team, TeamStatus, utcnow)

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


def recommended_or_409(session: Session, assignment_id: int) -> Assignment:
    a = get_or_404(session, Assignment, assignment_id)
    if a.status != AssignmentStatus.recommended:
        # Two operators clicking at once, or a stale screen: refuse, don't guess.
        raise HTTPException(status_code=409, detail=f"assignment {a.id} is {a.status}, not recommended")
    return a


def change_team(session: Session, a: Assignment, team_id: str) -> None:
    """Operator's "Change": same job, a different team of the same type."""
    old, new = session.get(Team, a.team_id), get_or_404(session, Team, team_id)
    if new.type != old.type:
        raise HTTPException(status_code=409, detail=f"{new.name} is {new.type}, this job needs {old.type}")
    if new.status == TeamStatus.returning or len(active_assignments(session, new.id)) >= new.capacity:
        raise HTTPException(status_code=409, detail=f"{new.name} has no free capacity")
    inc = session.get(Incident, a.incident_id)
    a.team_id = new.id
    a.eta_min = round(eta_min(new, inc), 1)
    a.cost = round(pair_cost(a.eta_min, inc.priority_score), 1)
    a.reason = f"{new.name}: ETA {a.eta_min:.0f} min; changed by operator from {old.name}"


@router.post("/assignments/{assignment_id}/approve")
def approve(assignment_id: int, body: ApproveIn, session: SessionDep) -> Assignment:
    a = recommended_or_409(session, assignment_id)
    before = snapshot(a)
    if body.team_id and body.team_id != a.team_id:
        change_team(session, a, body.team_id)

    a.status = AssignmentStatus.approved
    a.approved_by = body.operator
    a.approved_at = utcnow()
    session.get(Incident, a.incident_id).status = IncidentStatus.assigned
    refresh_team_status(session, session.get(Team, a.team_id))
    audit(session, f"operator:{body.operator}", "approve", a, before)
    session.commit()

    run_optimizer(session)  # this team is taken now: other recommendations may change
    session.refresh(a)
    return a


@router.post("/assignments/{assignment_id}/reject")
def reject(assignment_id: int, body: RejectIn, session: SessionDep) -> Assignment:
    a = recommended_or_409(session, assignment_id)
    before = snapshot(a)
    a.status = AssignmentStatus.rejected
    if body.reason:
        a.reason += f"; rejected: {body.reason}"
    audit(session, f"operator:{body.operator}", "reject", a, before)
    session.commit()

    run_optimizer(session)  # finds the next best team; this pair is now forbidden
    session.refresh(a)
    return a
