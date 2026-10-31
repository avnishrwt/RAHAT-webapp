"""The closed loop: recommend -> approve -> field update -> re-solve."""
from sqlmodel import select

from shared.schemas import AuditLog, Hazard, Incident, Team, TeamType

BOAT, MEDICAL = TeamType.boat, TeamType.medical


def setup_flood(session):
    session.add_all([
        Team(id="boat-a", name="Boat Team A", type=BOAT, lat=30.300, lng=78.030),
        Team(id="boat-b", name="Boat Team B", type=BOAT, lat=30.400, lng=78.030),
        Team(id="med-1", name="Medical Van 1", type=MEDICAL, lat=30.300, lng=78.030),
    ])
    dadi = Incident(lat=30.310, lng=78.030, needs=["rescue"], hazard=Hazard.flood, priority_score=31)
    session.add(dadi)
    session.commit()
    return dadi


def recommendation_for(client, incident_id):
    recs = [a for a in client.get("/assignments?status=recommended").json() if a["incident_id"] == incident_id]
    assert len(recs) == 1
    return recs[0]


def test_approve_marks_incident_assigned_and_team_busy(client, session):
    dadi = setup_flood(session)
    client.post("/optimize")
    rec = recommendation_for(client, dadi.id)

    r = client.post(f"/assignments/{rec['id']}/approve", json={"operator": "avnish"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved" and r.json()["approved_by"] == "avnish"

    session.expire_all()  # re-read what the endpoint wrote
    assert session.get(Incident, dadi.id).status == "assigned"
    assert session.get(Team, "boat-a").status == "busy"


def test_cannot_approve_twice(client, session):
    dadi = setup_flood(session)
    client.post("/optimize")
    rec = recommendation_for(client, dadi.id)
    client.post(f"/assignments/{rec['id']}/approve", json={"operator": "avnish"})
    again = client.post(f"/assignments/{rec['id']}/approve", json={"operator": "avnish"})
    assert again.status_code == 409


def test_operator_can_change_to_another_boat_but_not_a_van(client, session):
    dadi = setup_flood(session)
    client.post("/optimize")
    rec = recommendation_for(client, dadi.id)

    van = client.post(f"/assignments/{rec['id']}/approve", json={"operator": "avnish", "team_id": "med-1"})
    assert van.status_code == 409  # a medical van can't do a water rescue

    r = client.post(f"/assignments/{rec['id']}/approve", json={"operator": "avnish", "team_id": "boat-b"})
    assert r.status_code == 200
    assert r.json()["team_id"] == "boat-b"
    assert "changed by operator" in r.json()["reason"]


def test_reject_then_resolve_offers_a_different_team(client, session):
    dadi = setup_flood(session)
    client.post("/optimize")
    rec = recommendation_for(client, dadi.id)
    assert rec["team_id"] == "boat-a"

    r = client.post(f"/assignments/{rec['id']}/reject", json={"operator": "avnish", "reason": "boat A engine trouble"})
    assert r.json()["status"] == "rejected"
    assert recommendation_for(client, dadi.id)["team_id"] == "boat-b"  # re-solved automatically


def test_rescued_frees_team_and_resolves_incident(client, session):
    dadi = setup_flood(session)
    client.post("/optimize")
    rec = recommendation_for(client, dadi.id)
    client.post(f"/assignments/{rec['id']}/approve", json={"operator": "avnish"})

    r = client.patch("/teams/boat-a/status", json={"update": "rescued"})
    assert r.status_code == 200
    team = r.json()
    assert team["status"] == "free"
    assert (team["lat"], team["lng"]) == (30.310, 78.030)  # the team is now where dadi was

    session.expire_all()
    assert session.get(Incident, dadi.id).status == "resolved"


def test_rescued_triggers_next_assignment(client, session):
    # Only one boat: the second incident waits until Boat A finishes.
    session.add(Team(id="boat-a", name="Boat Team A", type=BOAT, lat=30.300, lng=78.030))
    first = Incident(lat=30.310, lng=78.030, needs=["rescue"], hazard=Hazard.flood, priority_score=31)
    second = Incident(lat=30.320, lng=78.030, needs=["rescue"], hazard=Hazard.flood, priority_score=20)
    session.add_all([first, second])
    session.commit()

    client.post("/optimize")
    rec = recommendation_for(client, first.id)
    client.post(f"/assignments/{rec['id']}/approve", json={"operator": "avnish"})
    assert client.get("/assignments?status=recommended").json() == []  # no boat left

    client.patch("/teams/boat-a/status", json={"update": "rescued"})
    assert recommendation_for(client, second.id)["team_id"] == "boat-a"


def test_no_one_here_marks_incident_false_and_frees_every_team(client, session):
    fake = Incident(lat=30.310, lng=78.030, needs=["rescue", "medical"], hazard=Hazard.flood, priority_score=40)
    session.add_all([
        Team(id="boat-a", name="Boat Team A", type=BOAT, lat=30.300, lng=78.030),
        Team(id="med-1", name="Medical Van 1", type=MEDICAL, lat=30.300, lng=78.030),
        fake,
    ])
    session.commit()
    for rec in client.post("/optimize").json():
        client.post(f"/assignments/{rec['id']}/approve", json={"operator": "avnish"})

    r = client.patch("/teams/boat-a/status", json={"update": "no_one_here"})
    assert r.status_code == 200

    session.expire_all()
    incident = session.get(Incident, fake.id)
    assert incident.status == "false"
    assert "field: no one here" in incident.red_flags
    assert session.get(Team, "med-1").status == "free"  # van is called back too


def test_status_update_without_assignment_is_409(client, session):
    setup_flood(session)
    assert client.patch("/teams/boat-a/status", json={"update": "rescued"}).status_code == 409
    assert client.patch("/teams/nope/status", json={"update": "rescued"}).status_code == 404


def test_every_decision_is_audited(client, session):
    dadi = setup_flood(session)
    client.post("/optimize")
    rec = recommendation_for(client, dadi.id)
    client.post(f"/assignments/{rec['id']}/approve", json={"operator": "avnish"})
    client.patch("/teams/boat-a/status", json={"update": "rescued"})

    log = session.exec(select(AuditLog).order_by(AuditLog.id)).all()
    assert [(e.actor, e.action) for e in log] == [("operator:avnish", "approve"), ("team:boat-a", "rescued")]
    assert log[0].before["status"] == "recommended" and log[0].after["status"] == "approved"
