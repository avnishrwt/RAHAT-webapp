from backend.optimizer import OptIncident, OptTeam, greedy, optimize, straight_line_eta
from shared.schemas import TeamType

BOAT, MEDICAL = TeamType.boat, TeamType.medical

# The pitch example (team brief p.2): travel minutes, team -> incident.
ETA = {("boat-a", 1): 5, ("boat-a", 2): 10,
       ("boat-b", 1): 6, ("boat-b", 2): 30}


def table_eta(team, inc):
    return ETA[(team.id, inc.id)]


FOOD = OptIncident(id=1, lat=0, lng=0, priority=5, team_types=(BOAT,))
DADI = OptIncident(id=2, lat=0, lng=0, priority=31, team_types=(BOAT,))
TEAM_A = OptTeam(id="boat-a", type=BOAT, lat=0, lng=0)
TEAM_B = OptTeam(id="boat-b", type=BOAT, lat=0, lng=0)


def by_incident(recs):
    return {r.incident_id: r for r in recs}


def test_optimizer_sends_team_a_to_dadi():
    recs = by_incident(optimize([FOOD, DADI], [TEAM_A, TEAM_B], eta=table_eta))
    assert recs[2].team_id == "boat-a" and recs[2].eta_min == 10
    assert recs[1].team_id == "boat-b" and recs[1].eta_min == 6


def test_greedy_baseline_makes_dadi_wait_30():
    # Food request arrived first, so greedy hands it the nearest team.
    recs = by_incident(greedy([FOOD, DADI], [TEAM_A, TEAM_B], eta=table_eta))
    assert recs[1].team_id == "boat-a"
    assert recs[2].team_id == "boat-b" and recs[2].eta_min == 30


def test_one_team_goes_to_the_critical_incident():
    recs = optimize([FOOD, DADI], [TEAM_A], eta=table_eta)
    assert [r.incident_id for r in recs] == [2]


def test_team_type_must_match():
    injured = OptIncident(id=3, lat=0, lng=0, priority=20, team_types=(MEDICAL,))
    assert optimize([injured], [TEAM_A], eta=lambda t, i: 5) == []


def test_incident_needing_boat_and_medical_gets_both():
    inc = OptIncident(id=4, lat=0, lng=0, priority=30, team_types=(BOAT, MEDICAL))
    medic = OptTeam(id="med-1", type=MEDICAL, lat=0, lng=0)
    recs = optimize([inc], [TEAM_A, medic], eta=lambda t, i: 5)
    assert sorted(r.team_id for r in recs) == ["boat-a", "med-1"]


def test_busy_team_and_empty_inputs():
    busy = OptTeam(id="boat-a", type=BOAT, lat=0, lng=0, capacity=0)
    assert optimize([DADI], [busy], eta=table_eta) == []
    assert optimize([], [TEAM_A]) == []


def test_straight_line_eta():
    team = OptTeam(id="t", type=BOAT, lat=30.0, lng=78.0, speed_kmph=20)
    inc = OptIncident(id=1, lat=30.1, lng=78.0, priority=1, team_types=(BOAT,))
    assert 33 < straight_line_eta(team, inc) < 34  # ~11.1 km at 20 km/h
