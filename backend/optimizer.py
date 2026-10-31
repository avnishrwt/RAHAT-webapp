"""Team assignment: min-cost flow over all incidents and teams at once (PRD 6.5).

Pure functions, no database: the API layer turns DB rows into OptIncident /
OptTeam, so this module is easy to test with known answers.
"""
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Callable

from ortools.graph.python import min_cost_flow

from shared.schemas import TeamType

LAMBDA = 2.0        # one priority point is worth 2 extra minutes of travel
IDLE_COST = 10_000  # a free team left unused costs more than any real trip
SCALE = 100         # OR-Tools needs integer costs: keep 2 decimals


@dataclass(frozen=True)
class OptIncident:
    id: int
    lat: float
    lng: float
    priority: float
    team_types: tuple[TeamType, ...]  # one team per type, e.g. (boat, medical)


@dataclass(frozen=True)
class OptTeam:
    id: str
    type: TeamType
    lat: float
    lng: float
    capacity: int = 1                 # incidents it can still take; busy = 0
    speed_kmph: float = 20.0


@dataclass(frozen=True)
class Recommendation:
    incident_id: int
    team_id: str
    eta_min: float
    cost: float
    reason: str


EtaFn = Callable[[OptTeam, OptIncident], float]


def straight_line_eta(team: OptTeam, inc: OptIncident) -> float:
    """Haversine distance / speed, in minutes. Demo stand-in for road routing."""
    dlat, dlng = radians(inc.lat - team.lat), radians(inc.lng - team.lng)
    a = sin(dlat / 2) ** 2 + cos(radians(team.lat)) * cos(radians(inc.lat)) * sin(dlng / 2) ** 2
    km = 2 * 6371 * asin(sqrt(a))
    return km / team.speed_kmph * 60


def pair_cost(eta_min: float, priority: float, lam: float = LAMBDA) -> float:
    # PRD 6.5: travel time - lambda x priority. Lower is better.
    return eta_min - lam * priority


def optimize(incidents: list[OptIncident], teams: list[OptTeam],
             eta: EtaFn = straight_line_eta, lam: float = LAMBDA,
             forbidden: set[tuple[int, str]] = frozenset()) -> list[Recommendation]:
    """Best team for every incident together, not one at a time.

    Graph: source -> team -> slot -> sink, where a slot is (incident, team type).
    Each team also has an "idle" arc straight to sink, so the flow always
    balances even when there are more teams than slots.
    forbidden holds (incident id, team id) pairs the operator rejected.
    """
    teams = [t for t in teams if t.capacity > 0]
    slots = [(inc, tt) for inc in incidents for tt in inc.team_types]
    if not teams or not slots:
        return []

    smcf = min_cost_flow.SimpleMinCostFlow()
    source, sink = 0, 1
    team_node = {t.id: 2 + i for i, t in enumerate(teams)}
    first_slot_node = 2 + len(teams)
    pairs = {}  # arc index -> (team, incident, eta, cost)

    for t in teams:
        smcf.add_arc_with_capacity_and_unit_cost(source, team_node[t.id], t.capacity, 0)
        smcf.add_arc_with_capacity_and_unit_cost(team_node[t.id], sink, t.capacity, IDLE_COST * SCALE)

    for k, (inc, team_type) in enumerate(slots):
        slot_node = first_slot_node + k
        smcf.add_arc_with_capacity_and_unit_cost(slot_node, sink, 1, 0)
        for t in teams:
            if t.type != team_type or (inc.id, t.id) in forbidden:
                continue  # filter: wrong skill (PRD 6.5 step 2) or operator said no
            e = eta(t, inc)
            c = pair_cost(e, inc.priority, lam)
            arc = smcf.add_arc_with_capacity_and_unit_cost(team_node[t.id], slot_node, 1, round(c * SCALE))
            pairs[arc] = (t, inc, e, c)

    supply = sum(t.capacity for t in teams)
    smcf.set_node_supply(source, supply)
    smcf.set_node_supply(sink, -supply)
    status = smcf.solve()
    if status != smcf.OPTIMAL:
        raise RuntimeError(f"min-cost flow failed with status {status}")

    recs = []
    for arc, (t, inc, e, c) in pairs.items():
        if smcf.flow(arc) > 0:
            recs.append(Recommendation(
                incident_id=inc.id, team_id=t.id, eta_min=round(e, 1), cost=round(c, 1),
                reason=f"{t.id} -> incident {inc.id}: ETA {e:.0f} min, priority {inc.priority:.0f}"))
    return sorted(recs, key=lambda r: (r.incident_id, r.team_id))


def greedy(incidents: list[OptIncident], teams: list[OptTeam],
           eta: EtaFn = straight_line_eta) -> list[Recommendation]:
    """Baseline to beat: in arrival order, each incident takes the nearest free team."""
    left = {t.id: t.capacity for t in teams}
    recs = []
    for inc in incidents:
        for team_type in inc.team_types:
            options = [t for t in teams if t.type == team_type and left[t.id] > 0]
            if not options:
                continue
            t = min(options, key=lambda t: eta(t, inc))
            e = eta(t, inc)
            left[t.id] -= 1
            recs.append(Recommendation(inc.id, t.id, round(e, 1), round(pair_cost(e, inc.priority), 1),
                                       "greedy: nearest free team"))
    return recs
