"""Read side of incidents: the operator's priority queue and the incident panel."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import col, select

from backend.db import SessionDep
from shared.schemas import Assignment, Incident, IncidentStatus, Message

router = APIRouter(tags=["incidents"])


class IncidentDetail(BaseModel):
    incident: Incident
    messages: list[Message]
    assignments: list[Assignment]


@router.get("/incidents")
def list_incidents(session: SessionDep, status: IncidentStatus | None = None) -> list[Incident]:
    """Priority queue: highest priority first; on a tie, the one waiting longest."""
    query = select(Incident).order_by(col(Incident.priority_score).desc(), col(Incident.created_at))
    if status is not None:
        query = query.where(Incident.status == status)
    return session.exec(query).all()


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: int, session: SessionDep) -> IncidentDetail:
    incident = session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"incident {incident_id} not found")
    messages = session.exec(
        select(Message).where(Message.incident_id == incident_id).order_by(col(Message.received_at))
    ).all()
    assignments = session.exec(select(Assignment).where(Assignment.incident_id == incident_id)).all()
    return IncidentDetail(incident=incident, messages=messages, assignments=assignments)
