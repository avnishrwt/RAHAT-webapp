"""Team registry and field updates from the team PWA (PRD FR08, FR12)."""
from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from backend.allocation import ACTIVE, active_assignments, refresh_team_status, run_optimizer
from backend.audit import audit, snapshot
from backend.db import SessionDep, get_or_404
from shared.schemas import (Assignment, AssignmentStatus, FieldUpdate, Incident, IncidentStatus,
                            Team, TeamStatusIn, utcnow)

router = APIRouter(tags=["teams"])


@router.get("/teams")
def list_teams(session: SessionDep) -> list[Team]:
    return session.exec(select(Team).order_by(Team.id)).all()


@router.patch("/teams/{team_id}/status")
def field_update(team_id: str, body: TeamStatusIn, session: SessionDep) -> Team:
    team = get_or_404(session, Team, team_id)
    team.last_seen = utcnow()
    if body.lat is not None and body.lng is not None:
        team.lat, team.lng = body.lat, body.lng

    jobs = [a for a in active_assignments(session, team.id)
            if body.assignment_id is None or a.id == body.assignment_id]
    if len(jobs) != 1:
        problem = "no active assignment" if not jobs else "several active assignments: send assignment_id"
        raise HTTPException(status_code=409, detail=f"{team.name} has {problem}")
    job = jobs[0]
    inc = session.get(Incident, job.incident_id)
    before = snapshot(inc)

    if body.update in (FieldUpdate.reached, FieldUpdate.rescued):
        team.lat, team.lng = inc.lat, inc.lng  # the team is at the incident now

    if body.update == FieldUpdate.rescued:
        job.status = AssignmentStatus.done
        others = session.exec(select(Assignment).where(
            Assignment.incident_id == inc.id, Assignment.id != job.id,
            col(Assignment.status).in_(ACTIVE))).all()
        if not others:  # e.g. the medical van may still be on its way
            inc.status = IncidentStatus.resolved

    elif body.update == FieldUpdate.no_one_here:
        # The report was false: call back EVERY team sent to it, not just this one.
        # Senders of this incident's messages can be found later for reputation.
        inc.status = IncidentStatus.false
        inc.red_flags = [*inc.red_flags, "field: no one here"]
        for a in session.exec(select(Assignment).where(
                Assignment.incident_id == inc.id, col(Assignment.status).in_(ACTIVE))).all():
            a.status = AssignmentStatus.done
            if a.team_id != team.id:
                refresh_team_status(session, session.get(Team, a.team_id))

    # reached / need_backup change no status: they are logged, and chunk 5
    # pushes them to the operator's screen live.

    refresh_team_status(session, team)
    audit(session, f"team:{team.id}", body.update, inc, before)
    session.commit()

    if body.update in (FieldUpdate.rescued, FieldUpdate.no_one_here):
        run_optimizer(session)  # a team is free: give it the next job
    session.refresh(team)
    return team
