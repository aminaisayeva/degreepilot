from datetime import datetime

from sqlmodel import Field, SQLModel


class DirectorySync(SQLModel, table=True):
    """One row per (subject, term) tracking when we last pulled the live
    Columbia Directory of Classes for that pair."""

    id: int | None = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    term: str = Field(index=True)  # e.g. "Fall2026"
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "ok"
    courses_fetched: int = 0
    courses_inserted: int = 0
    courses_updated: int = 0
    error: str | None = None
