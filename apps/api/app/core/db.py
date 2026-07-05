from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

_settings = get_settings()

_connect_args: dict = {}
if _settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(_settings.database_url, echo=False, connect_args=_connect_args)


def init_db() -> None:
    # Import models so SQLModel.metadata is populated before create_all.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate(engine)


def _migrate(eng) -> None:
    """Additive column migrations for databases created by older versions
    (create_all never alters existing tables)."""
    from sqlalchemy import inspect, text

    insp = inspect(eng)
    if "student" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("student")}
        if "programs" not in cols:
            with eng.begin() as conn:
                conn.execute(text("ALTER TABLE student ADD COLUMN programs JSON"))
        if "waived_courses" not in cols:
            with eng.begin() as conn:
                conn.execute(text("ALTER TABLE student ADD COLUMN waived_courses JSON"))


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
