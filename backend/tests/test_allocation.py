from datetime import datetime, timezone

from backend.dispatch import team_types_for
from shared.schemas import Assignment, AssignmentStatus, Hazard, Incident, Team, TeamType

BOAT, MEDICAL, RELIEF = TeamType.boat, TeamType.medical, TeamType.relief


def test_need_to_team_type_rules():
    assert team_types_for(["rescue"], Hazard.flood) == (BOAT,)
    assert team_types_for(["rescue", "medical"], Hazard.flood) == (BOAT, MEDICAL)
    assert team_types_for(["food", "water"], None) == (RELIEF,)
    assert team_types_for(["rescue"], Hazard.fire) == (TeamType.fire,)
    assert team_types_for(["rescue"], Hazard.collapse) == (TeamType.search_rescue,)
    assert team_types_for([], None) == ()  # "kab tak barish rukegi?" needs no team


def add_teams(session):
    session.add_all([
        Team(id="boat-a", name="Boat Team A", type=BOAT, lat=30.300, lng=78.030),
        Team(id="boat-b", name="Boat Team B", type=BOAT, lat=30.400, lng=78.030),
        Team(id="relief-1", name="Relief Truck 1", type=RELIEF, lat=30.300, lng=78.040),
    ])


def add_incident(session, **fields):
    inc = Incident(lat=30.310, lng=78.030, **fields)
    session.add(inc)
    session.commit()
    return inc


def test_optimize_recommends_nearest_boat_for_dadi(client, session):
    add_teams(session)
    dadi = add_incident(session, needs=["rescue"], hazard=Hazard.flood, priority_score=31, confidence=0.86)
    food = add_incident(session, needs=["food"], priority_score=8, confidence=0.7)

    r = client.post("/optimize")
    assert r.status_code == 200
    recs = {a["incident_id"]: a for a in r.json()}
    assert recs[dadi.id]["team_id"] == "boat-a"
    assert recs[dadi.id]["status"] == "recommended"
    assert recs[food.id]["team_id"] == "relief-1"


def test_running_optimize_twice_does_not_duplicate(client, session):
    add_teams(session)
    add_incident(session, needs=["rescue"], hazard=Hazard.flood, priority_score=31)
    client.post("/optimize")
    client.post("/optimize")
    assert len(client.get("/assignments?status=recommended").json()) == 1


def test_low_confidence_matrix(client, session):
    add_teams(session)
    # High priority, low confidence: still gets a team, marked standby + verify.
    lone = add_incident(session, needs=["rescue"], hazard=Hazard.flood, priority_score=40, confidence=0.2)
    # Low priority, low confidence: no team until callback / operator review.
    add_incident(session, needs=["food"], priority_score=5, confidence=0.2)

    recs = client.post("/optimize").json()
    assert [a["incident_id"] for a in recs] == [lone.id]
    assert "verify" in recs[0]["reason"]


def test_busy_team_is_not_reused_and_missing_type_is_filled(client, session):
    add_teams(session)
    session.add(Team(id="med-1", name="Medical Van 1", type=MEDICAL, lat=30.300, lng=78.030))
    inc = add_incident(session, needs=["rescue", "medical"], hazard=Hazard.flood, priority_score=40)
    # Boat A is already approved for this incident; only the medical slot is open.
    session.add(Assignment(incident_id=inc.id, team_id="boat-a", cost=0, eta_min=5,
                           status=AssignmentStatus.approved,
                           approved_at=datetime.now(timezone.utc)))
    session.commit()

    recs = client.post("/optimize").json()
    assert [a["team_id"] for a in recs] == ["med-1"]


def test_incident_without_map_pin_waits(client, session):
    add_teams(session)
    session.add(Incident(location_text="mandir ke peeche", needs=["rescue"], hazard=Hazard.flood, priority_score=40))
    session.commit()
    assert client.post("/optimize").json() == []


def test_seed_loads_demo_teams_and_can_rerun(session):
    from backend.seed import DEMO_TEAMS, load_teams
    load_teams(session, DEMO_TEAMS)
    load_teams(session, DEMO_TEAMS)  # running twice must not duplicate or crash
    relief = session.get(Team, "relief-1")
    assert relief.type == RELIEF and relief.capacity == 3


def test_get_teams(client, session):
    add_teams(session)
    session.commit()
    assert [t["id"] for t in client.get("/teams").json()] == ["boat-a", "boat-b", "relief-1"]
