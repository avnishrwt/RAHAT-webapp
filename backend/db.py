"""Database engine and session. Every endpoint gets its session from get_session()."""
import os

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

import shared.schemas  # noqa: F401  (registers the tables on SQLModel.metadata)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rahat.db")

# FastAPI serves requests on several threads; SQLite allows that only with this flag.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
