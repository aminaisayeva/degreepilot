from fastapi import APIRouter

from app.api.routes import admin, advisor, audit, courses, health, plans, requirements, students

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(requirements.router, prefix="/requirements", tags=["requirements"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(audit.router, prefix="/students", tags=["audit"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(advisor.router, prefix="/advisor", tags=["advisor"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
