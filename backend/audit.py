"""Audit log: every recommendation decision and field update, with who and when (PRD FR18)."""
from sqlmodel import Session, SQLModel

from shared.schemas import AuditLog


def snapshot(obj: SQLModel) -> dict:
    # mode="json" turns datetimes and enums into plain strings the JSON column can hold.
    return obj.model_dump(mode="json")


def audit(session: Session, actor: str, action: str, obj: SQLModel, before: dict | None) -> None:
    """Record obj's change. The caller commits, so the log and the change save together."""
    session.add(AuditLog(actor=actor, action=action, entity=type(obj).__name__.lower(),
                         entity_id=str(obj.id), before=before, after=snapshot(obj)))
