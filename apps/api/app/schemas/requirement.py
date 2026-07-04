from pydantic import BaseModel

from app.models.requirement import RequirementType


class RequirementRead(BaseModel):
    id: int
    program: str
    name: str
    type: RequirementType
    courses: list[str]
    category: str | None
    credits_required: float
    count_required: int
    display_order: int
    notes: str

    model_config = {"from_attributes": True}
