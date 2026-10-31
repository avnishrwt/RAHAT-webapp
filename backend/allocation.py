"""Glue between the database and the optimizer: rows in, Assignment rows out."""
from collections import Counter, defaultdict

from sqlmodel import Session, col, select

from backend.dispatch import team_types_for
from backend.optimizer import OptIncident, OptTeam, optimize, straight_line_eta
from shared.schemas import (Assignment, AssignmentStatus, Incident, IncidentStatus, Team,
                            TeamStatus, TeamType)

ACTIVE = (AssignmentStatus.approved, AssignmentStatus.en_route)

# PRD 6.3 action matrix. Placeholders until Mayank fixes the priority scale.
LOW_CONFIDENCE = 0.4
HIGH_PRIORITY = 25

# Demo assumptions for straight-line ETA, not measured speeds.
SPEED_KMPH = {TeamType.boat: 12, TeamType.medical: 30, TeamType.relief: 25,
              TeamType.search_rescue: 25, TeamType.fire: 30}


def active_assignments(session: Session, team_id: str) -> list[Assignment]:
    return session.exec(select(Assignment).where(
        Assignment.team_id == team_id, col(Assignment.status).in_(ACTIVE))).all()


def refresh_team_status(session: Session, team: Team) -> None:
    """Busy once its active jobs fill its capacity, free otherwise."""
    full = len(active_assignments(session, team.id)) >= team.capacity
    team.status = TeamStatus.busy if full else TeamStatus.free


def eta_min(team: Team, inc: Incident) -> float:
    """ETA for a team the operator picked by hand (the optimizer computes its own)."""
    return straight_line_eta(
        OptTeam(id=team.id, type=team.type, lat=team.lat, lng=team.lng, speed_kmph=SPEED_KMPH[team.type]),
        OptIncident(id=inc.id, lat=inc.lat, lng=inc.lng, priority=inc.priority_score, team_types=()))


def run_optimizer(session: Session) -> list[Assignment]:
    """Replace all unapproved recommendations with a fresh optimal set."""
    # Recommendations nobody approved are out of date once anything changes.
    for old in session.exec(select(Assignment).where(Assignment.status == AssignmentStatus.recommended)):
        session.delete(old)

    teams = {t.id: t for t in session.exec(select(Team)).all()}
    active = session.exec(select(Assignment).where(col(Assignment.status).in_(ACTIVE))).all()
    load = Counter(a.team_id for a in active)
    covered = defaultdict(set)  # incident id -> team types already on their way
    for a in active:
        covered[a.incident_id].add(teams[a.team_id].type)

    opt_teams = [
        OptTeam(id=t.id, type=t.type, lat=t.lat, lng=t.lng,
                capacity=max(t.capacity - load[t.id], 0), speed_kmph=SPEED_KMPH[t.type])
        for t in teams.values() if t.status != TeamStatus.returning
    ]

    incidents = session.exec(
        select(Incident).where(col(Incident.status).in_((IncidentStatus.open, IncidentStatus.assigned)))
    ).all()
    opt_incidents = []
    for inc in incidents:
        if inc.lat is None or inc.lng is None:
            continue  # no map pin yet: operator confirms the location first
        if inc.confidence < LOW_CONFIDENCE and inc.priority_score < HIGH_PRIORITY:
            continue  # low/low: callback + operator review before any team moves
        needed = tuple(tt for tt in team_types_for(inc.needs, inc.hazard) if tt not in covered[inc.id])
        if needed:
            opt_incidents.append(OptIncident(id=inc.id, lat=inc.lat, lng=inc.lng,
                                             priority=inc.priority_score, team_types=needed))

    # Pairs the operator rejected stay rejected for the rest of the incident.
    rejected = session.exec(select(Assignment.incident_id, Assignment.team_id)
                            .where(Assignment.status == AssignmentStatus.rejected)).all()
    forbidden = {(incident_id, team_id) for incident_id, team_id in rejected}

    by_id = {inc.id: inc for inc in incidents}
    rows = []
    for rec in optimize(opt_incidents, opt_teams, forbidden=forbidden):
        reason = f"{teams[rec.team_id].name}: ETA {rec.eta_min:.0f} min, priority {by_id[rec.incident_id].priority_score:.0f}"
        if by_id[rec.incident_id].confidence < LOW_CONFIDENCE:
            reason += "; standby, verify by callback in parallel"
        rows.append(Assignment(incident_id=rec.incident_id, team_id=rec.team_id,
                               cost=rec.cost, eta_min=rec.eta_min, reason=reason))

    session.add_all(rows)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows
