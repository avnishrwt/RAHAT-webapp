from shared.schemas import Incident, IncidentStatus, Message

DADI = "Bhai Rampur gali 3 mein meri dadi phasi hai, paani 5 feet hai"


def test_message_is_stored_with_hashed_sender(client, session):
    r = client.post("/messages", json={"channel": "whatsapp", "sender": "+91 98765-43210", "raw_text": DADI})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "new" and body["raw_text"] == DADI
    assert "98765" not in body["sender_hash"]

    stored = session.get(Message, body["id"])
    assert stored.sender_hash == body["sender_hash"]


def test_same_phone_in_different_formats_gets_same_hash(client):
    a = client.post("/messages", json={"channel": "sms", "sender": "+91 98765 43210", "raw_text": "help"})
    b = client.post("/messages", json={"channel": "sms", "sender": "09876543210", "raw_text": "help"})
    assert a.json()["sender_hash"] == b.json()["sender_hash"]


def test_time_without_timezone_is_read_as_ist(client):
    r = client.post("/messages", json={"channel": "whatsapp", "sender_hash": "a91f",
                                       "received_at": "2026-11-10T02:04:11", "raw_text": DADI})
    assert r.json()["received_at"].startswith("2026-11-09T20:34:11")  # 02:04 IST = 20:34 UTC


def test_bad_messages_are_rejected(client):
    no_sender = client.post("/messages", json={"channel": "sms", "raw_text": "help"})
    no_text = client.post("/messages", json={"channel": "sms", "sender": "9876543210"})
    bad_channel = client.post("/messages", json={"channel": "pigeon", "sender": "1", "raw_text": "x"})
    assert no_sender.status_code == no_text.status_code == bad_channel.status_code == 422


def test_missed_call_needs_no_text(client):
    r = client.post("/messages", json={"channel": "missed_call", "sender": "9876543210"})
    assert r.status_code == 201


def test_incident_queue_is_sorted_by_priority(client, session):
    session.add_all([
        Incident(location_text="food request", priority_score=12),
        Incident(location_text="dadi", priority_score=31),
        Incident(location_text="done already", priority_score=50, status=IncidentStatus.resolved),
    ])
    session.commit()

    everything = [i["location_text"] for i in client.get("/incidents").json()]
    assert everything == ["done already", "dadi", "food request"]

    open_only = [i["location_text"] for i in client.get("/incidents?status=open").json()]
    assert open_only == ["dadi", "food request"]


def test_incident_detail_includes_its_messages(client, session):
    inc = Incident(location_text="Rampur, Gali 3", priority_score=31)
    session.add(inc)
    session.commit()
    for text in [DADI, "rampur gali 3 old lady trapped plz"]:
        session.add(Message(channel="whatsapp", sender_hash="x", raw_text=text, incident_id=inc.id))
    session.add(Message(channel="sms", sender_hash="y", raw_text="khana chahiye"))  # other incident
    session.commit()

    r = client.get(f"/incidents/{inc.id}")
    assert r.status_code == 200
    assert len(r.json()["messages"]) == 2
    assert client.get("/incidents/999").status_code == 404
