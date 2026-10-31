"""RAHAT data model: the one contract every module imports.

Tables follow PRD section 9. Change a field here, tell the whole team.
"""
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, model_validator
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


class Need(StrEnum):
    rescue = "rescue"
    medical = "medical"
    food = "food"
    water = "water"
    medicine = "medicine"
    shelter = "shelter"


class Vulnerable(StrEnum):
    elderly = "elderly"
    child = "child"
    disabled = "disabled"
    pregnant = "pregnant"


class Hazard(StrEnum):
    flood = "flood"
    fire = "fire"
    collapse = "collapse"
    landslide = "landslide"


class Medical(StrEnum):
    life_threatening = "life_threatening"
    serious = "serious"
    minor = "minor"


class Urgency(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class ExtractedBy(StrEnum):
    llm = "llm"
    rules = "rules"      # keyword fallback / baseline


class FieldUpdate(StrEnum):
    """One-tap buttons on the team PWA (PRD FR12)."""
    reached = "reached"
    rescued = "rescued"
    no_one_here = "no_one_here"
    need_backup = "need_backup"


# ---------- extractor output (contract between agents and backend) ----------

class ExtractedFields(BaseModel):
    """What the Extractor agent returns for ONE message.

    Unknown means None / empty list. Never guess (PRD FR02).
    Enum fields reject anything else, so lowercase LLM output before validating.
    """
    location_text: str | None = None
    lat: float | None = None
    lng: float | None = None
    people_count: int | None = None
    vulnerable: list[Vulnerable] = []
    needs: list[Need] = []          # one message can need several: rescue + medical
    hazard: Hazard | None = None
    hazard_detail: str | None = None  # free text, e.g. "water ~5 ft"
    medical: Medical | None = None
    urgency: Urgency | None = None
    language: str | None = None
    extracted_by: ExtractedBy | None = None


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
    # JSON lists hold plain strings: the Vulnerable / Need values above.
    vulnerable: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    needs: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    hazard: Hazard | None = None
    hazard_detail: str | None = None
    medical: Medical | None = None
    urgency: Urgency | None = None
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


# ---------- API request bodies ----------

class MessageIn(BaseModel):
    """Body of POST /messages. Replay script, simulator page and call buttons all send this."""
    channel: Channel
    received_at: datetime | None = None   # no timezone given = IST; missing = now
    sender: str | None = None             # raw phone: hashed by the backend, never stored
    sender_hash: str | None = None        # replay data may arrive already hashed
    raw_text: str | None = None
    audio_url: str | None = None

    @model_validator(mode="after")
    def check_required(self):
        if not (self.sender or self.sender_hash):
            raise ValueError("give sender or sender_hash")
        # A missed call or proactive check carries no content; everything else must.
        silent = {Channel.missed_call, Channel.proactive_check}
        if self.channel not in silent and not (self.raw_text or self.audio_url):
            raise ValueError("give raw_text or audio_url")
        return self


class ApproveIn(BaseModel):
    """Body of POST /assignments/{id}/approve. A team_id here = the operator's "Change"."""
    operator: str
    team_id: str | None = None


class RejectIn(BaseModel):
    operator: str
    reason: str | None = None


class TeamStatusIn(BaseModel):
    """Body of PATCH /teams/{id}/status, sent by the team PWA (queued while offline)."""
    update: FieldUpdate
    assignment_id: int | None = None   # only needed if the team has several jobs
    lat: float | None = None
    lng: float | None = None
