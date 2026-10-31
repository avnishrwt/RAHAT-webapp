"""Need -> team type rules (PRD 6.5 step 1).

Default rules so the loop runs end to end. Mayank's Dispatcher agent can
replace team_types_for() later; the optimizer only needs the tuple it returns.
"""
from shared.schemas import Hazard, TeamType

RELIEF_NEEDS = {"food", "water", "medicine", "shelter"}


def team_types_for(needs: list[str], hazard: Hazard | None) -> tuple[TeamType, ...]:
    types: list[TeamType] = []
    if hazard == Hazard.fire:
        types.append(TeamType.fire)
    if hazard in (Hazard.collapse, Hazard.landslide):
        types.append(TeamType.search_rescue)
    if "rescue" in needs and not types:
        # People in water need a boat; anywhere else, search and rescue.
        types.append(TeamType.boat if hazard == Hazard.flood else TeamType.search_rescue)
    if "medical" in needs:
        types.append(TeamType.medical)
    if RELIEF_NEEDS & set(needs):
        types.append(TeamType.relief)
    return tuple(types)
