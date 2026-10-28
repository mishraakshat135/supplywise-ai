"""Test setup: a fresh in-memory SQLite database for every test."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.database import Base, get_db
from app.main import app
from app.rag.factory import get_retriever


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    def _get_db():
        yield db_session
    app.dependency_overrides[get_db] = _get_db
    # fresh keyword index per test
    retr = get_retriever()
    for c in list({c[0] for c in getattr(retr, "_chunks", [])}):
        retr.remove_document(c)
    yield TestClient(app)
    app.dependency_overrides.clear()
