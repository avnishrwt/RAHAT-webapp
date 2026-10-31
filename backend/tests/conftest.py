import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.db import get_session
from backend.main import app


@pytest.fixture
def session():
    # StaticPool: every connection reuses ONE in-memory database.
    # Without it, each new connection would get its own empty database.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(session):
    # Endpoints get the test database instead of rahat.db.
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)  # no `with`: skips lifespan, so rahat.db is never created
    app.dependency_overrides.clear()
