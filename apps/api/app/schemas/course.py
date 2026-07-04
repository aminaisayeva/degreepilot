from pydantic import BaseModel


class CourseRead(BaseModel):
    code: str
    title: str
    department: str
    credits: float
    description: str
    workload_level: int
    offered_terms: list[str]
    prerequisites: list[list[str]]
    categories: list[str]
    career_tags: list[str]

    model_config = {"from_attributes": True}
