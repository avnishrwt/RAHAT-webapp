"""Load teams into the database.

    python -m backend.seed                      # demo teams
    python -m backend.seed data/teams.json      # Hardik's team file
"""
import json
import sys
from pathlib import Path

from sqlmodel import Session

from backend.db import create_db, engine
from shared.schemas import Team

DEMO_TEAMS = Path(__file__).parent / "fixtures" / "teams_demo.json"


def load_teams(session: Session, path: Path) -> int:
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        session.merge(Team.model_validate(row))  # insert, or update the team with this id
    session.commit()
    return len(rows)


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEMO_TEAMS
    create_db()
    with Session(engine) as session:
        print(f"loaded {load_teams(session, path)} teams from {path}")
