from datetime import datetime

from sqlmodel import Field, SQLModel


class AccuracyCheck(SQLModel, table=True):
    """A human verification mark for one catalog entity.

    entity_type: "course" (entity_key = course code) or
                 "requirement" (entity_key = "<program>/<requirement name>").
    status: "verified" | "incorrect" — "unchecked" is represented by absence.
    """

    id: int | None = Field(default=None, primary_key=True)
    entity_type: str = Field(index=True)
    entity_key: str = Field(index=True)
    status: str
    notes: str = ""
    checked_at: datetime = Field(default_factory=datetime.utcnow)
