from sqlmodel import Session, SQLModel, create_engine, select

from shared.schemas import Channel, ExtractedFields, Incident, Message, MessageStatus


def make_session() -> Session:
    engine = create_engine("sqlite://")  # in-memory, gone after the test
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_message_joins_incident_and_json_lists_round_trip():
    s = make_session()
    inc = Incident(location_text="Rampur, Gali 3", vulnerable=["elderly"], needs=["rescue"])
    s.add(inc)
    s.commit()

    for text in ["Bhai Rampur gali 3 mein meri dadi phasi hai", "rampur gali 3 old lady trapped plz"]:
        s.add(Message(channel=Channel.whatsapp, sender_hash="abc", raw_text=text,
                      incident_id=inc.id, status=MessageStatus.merged))
    s.commit()

    got = s.get(Incident, inc.id)
    assert got.vulnerable == ["elderly"]
    assert got.confidence == 0.5  # lone/new report starts neutral
    msgs = s.exec(select(Message).where(Message.incident_id == inc.id)).all()
    assert len(msgs) == 2


def test_extractor_unknown_fields_stay_empty():
    f = ExtractedFields(location_text="sector 4 mandir ke peeche")
    assert f.people_count is None and f.needs == []
