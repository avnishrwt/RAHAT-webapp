"""POST /messages: every citizen channel enters RAHAT here (PRD FR01)."""
from datetime import timedelta, timezone

from fastapi import APIRouter

from backend.db import SessionDep
from backend.privacy import hash_sender
from shared.schemas import Message, MessageIn, utcnow

# Fixed offset, not ZoneInfo: India has no daylight saving, and Windows
# Python has no timezone database unless the tzdata package is installed.
IST = timezone(timedelta(hours=5, minutes=30))

router = APIRouter(tags=["messages"])


@router.post("/messages", status_code=201)
def ingest_message(body: MessageIn, session: SessionDep) -> Message:
    received = body.received_at or utcnow()
    if received.tzinfo is None:
        received = received.replace(tzinfo=IST)

    msg = Message(
        channel=body.channel,
        received_at=received,
        sender_hash=body.sender_hash or hash_sender(body.sender),
        raw_text=body.raw_text,
        audio_url=body.audio_url,
    )
    # Store first, process later: if an agent crashes, the message is still saved (PRD 7).
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg
