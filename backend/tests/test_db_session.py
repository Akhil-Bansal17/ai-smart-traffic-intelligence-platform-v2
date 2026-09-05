"""
Confirms the DB session machinery (engine creation, get_db generator
lifecycle) works mechanically. Uses SQLite in-memory rather than the
real Postgres so this test suite doesn't require a live database
server to run - the real Postgres connection itself is verified
separately via `alembic current` (see PROJECT_STATUS.md).
"""
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def test_get_db_generator_yields_and_closes_a_working_session():
    test_engine = create_engine("sqlite:///:memory:", future=True)
    TestSessionLocal = sessionmaker(bind=test_engine, future=True)

    def get_test_db() -> Generator:
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    gen = get_test_db()
    db = next(gen)
    result = db.execute(text("SELECT 1")).scalar()
    assert result == 1

    # Draining the generator should close the session without error
    try:
        next(gen)
    except StopIteration:
        pass
