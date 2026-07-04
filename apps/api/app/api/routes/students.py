from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentRead, StudentUpdate

router = APIRouter()


@router.post("", response_model=StudentRead)
def create_student(payload: StudentCreate, session: Session = Depends(get_session)) -> Student:
    student = Student(**payload.model_dump())
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentRead)
def get_student(student_id: int, session: Session = Depends(get_session)) -> Student:
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    return student


@router.put("/{student_id}", response_model=StudentRead)
def update_student(
    student_id: int, payload: StudentUpdate, session: Session = Depends(get_session)
) -> Student:
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(student, k, v)
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


@router.get("", response_model=list[StudentRead])
def list_students(session: Session = Depends(get_session)) -> list[Student]:
    return list(session.exec(select(Student)).all())
