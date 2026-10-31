"""RAHAT data model: the one contract every module imports.

Tables follow PRD section 9. Change a field here, tell the whole team.
"""
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel
from sqlmodel import JSON, Column, Field, SQLModel


def utcnow() -> datetime:
    # SQLModel 0.0.48 rejects naive datetimes; it stores aware ones as UTC.
    return datetime.now(timezone.utc)


# ---------- enums (allowed values for status / type fields) ----------

class Channel(StrEnum):
    sms = "sms"
    whatsapp = "whatsapp"
    voice = "voice"
    web = "web"
    ivr = "ivr"
    missed_call = "missed_call"
    proactive_check = "proactive_check"


class MessageStatus(StrEnum):
    new = "new"          # stored, not processed yet
    merged = "merged"    # attached to an incident
    review = "review"    # outlier: a human must look at it


class IncidentStatus(StrEnum):
    open = "open"
    assigned = "assigned"
    resolved = "resolved"
    false = "false"      # field team found no one


class TeamType(StrEnum):
    boat = "boat"
    medical = "medical"
    relief = "relief"
    search_rescue = "search_rescue"
    fire = "fire"


class TeamStatus(StrEnum):
    free = "free"
    busy = "busy"
    returning = "returning"


class AssignmentStatus(StrEnum):
    recommended = "recommended"
    approved = "approved"
    en_route = "en_route"
    done = "done"
    rejected = "rejected"


# ---------- extractor output (contract between agents and backend) ----------

class ExtractedFields(BaseModel):
    """What the Extractor agent returns for ONE message.

    Unknown means None / empty list. Never guess (PRD FR02).
    """
    location_text: str | None = None
    people_count: int | None = None
    vulnerable: list[str] = []      # "elderly", "child", "disabled", "pregnant"
    needs: list[str] = []           # "rescue", "medical", "food", "water", "shelter"
    hazard: str | None = None       # free text, e.g. "water ~5 ft"
    medical: str | None = None      # "life_threatening", "serious", "minor"
    urgency: str | None = None      # "critical", "high", "medium", "low"
    language: str | None = None


# ---------- database tables ----------
# JSON columns: reassign the whole list/dict to save a change
# (incident.red_flags = [...]); .append() in place is not detected.

class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    channel: Channel
    received_at: datetime = Field(default_factory=utcnow)
    sender_hash: str = Field(index=True)
    raw_text: str | None = None
    audio_url: str | None = None
    language: str | None = None
    extracted: dict | None = Field(default=None, sa_column=Column(JSON))
    incident_id: int | None = Field(default=None, foreign_key="incident.id", index=True)
    status: MessageStatus = MessageStatus.new


class Incident(SQLModel, table=True):
    # message_ids is not stored: query Message.incident_id instead,
    # so the link lives in one place only.
    id: int | None = Field(default=None, primary_key=True)
    location_text: str | None = None
    lat: float | None = None
    lng: float | None = None
    people_count: int | None = None
    vulnerable: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    needs: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    hazard: str | None = None
    medical: str | None = None
    priority_score: float = 0.0
    priority_breakdown: dict = Field(default_factory=dict, sa_column=Column(JSON))
    confidence: float = 0.5          # neutral start: a lone report is not "low"
    red_flags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: IncidentStatus = IncidentStatus.open
    created_at: datetime = Field(default_factory=utcnow)


class Team(SQLModel, table=True):
    id: str = Field(primary_key=True)  # e.g. "boat-a", from data/teams.json
    name: str                          # e.g. "Boat Team A"
    type: TeamType
    equipment: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    capacity: int = 1                  # incidents it can take at once
    lat: float
    lng: float
    status: TeamStatus = TeamStatus.free
    last_seen: datetime = Field(default_factory=utcnow)


class Assignment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: int = Field(foreign_key="incident.id", index=True)
    team_id: str = Field(foreign_key="team.id", index=True)
    cost: float
    eta_min: float
    reason: str = ""                   # shown to the operator
    recommended_at: datetime = Field(default_factory=utcnow)
    approved_by: str | None = None
    approved_at: datetime | None = None
    status: AssignmentStatus = AssignmentStatus.recommended


class VulnerableResident(SQLModel, table=True):
    # Opt-in list only, minimal fields (PRD section 7, Consent).
    id: int | None = Field(default=None, primary_key=True)
    area: str
    lat: float | None = None
    lng: float | None = None
    phone_hash: str
    needs: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    consent_at: datetime
    last_check_at: datetime | None = None
    last_check_result: str | None = None   # "ok", "no_answer", "needs_help"


class AuditLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    at: datetime = Field(default_factory=utcnow)
    actor: str                         # "operator:avnish", "team:boat-a", "system"
    action: str                        # "approve", "reject", "status_change", ...
    entity: str                        # "assignment", "incident", "team"
    entity_id: str
    before: dict | None = Field(default=None, sa_column=Column(JSON))
    after: dict | None = Field(default=None, sa_column=Column(JSON))
