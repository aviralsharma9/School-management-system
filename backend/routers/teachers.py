from fastapi import APIRouter, HTTPException, Depends
from backend.database import get_db
from backend.auth.dependencies import require_management_or_principal
from backend.schemas.teacher import (
    TeacherCreate,
    TeacherUpdate,
    TeacherProfileResponse
)
from backend.services import teacher_service

router = APIRouter()

@router.post("/teachers")
def create_teacher(
    data: TeacherCreate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):
    return teacher_service.create_teacher(data, connection)
 
 
@router.put("/teachers/{teacher_id}")
def update_teacher(
    teacher_id: str,
    data: TeacherUpdate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):
    return teacher_service.update_teacher(teacher_id, data, connection)

@router.get(
    "/teachers/deactivated",
    response_model=list[TeacherProfileResponse]
)
def get_deactivated_teachers(
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                t.teacher_id,
                p.name,
                u.is_active
            FROM teachers t
            JOIN users u
                ON t.user_id = u.id
            JOIN profiles p
                ON t.user_id = p.user_id    
            WHERE u.is_active = FALSE
            ORDER BY t.teacher_id;
            """
        )

        teachers = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "teacher_id": teacher[0],
            "name": teacher[1],
            "is_active": teacher[2]
        }
        for teacher in teachers
    ]

@router.get(
    "/teachers",
    response_model=list[TeacherProfileResponse]
)
def get_teachers(
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                t.teacher_id,
                p.name,
                u.is_active
            FROM teachers t
            JOIN users u
                ON t.user_id = u.id
            JOIN profiles p
                ON t.user_id = p.user_id    
            WHERE u.is_active = TRUE
            ORDER BY t.teacher_id;
            """
        )

        teachers = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "teacher_id": teacher[0],
            "name": teacher[1],
            "is_active": teacher[2]
        }
        for teacher in teachers
    ]
 
@router.get(
    "/teachers/{teacher_id}",
    response_model=TeacherProfileResponse
)
def get_teacher(
    teacher_id: str,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                t.teacher_id,
                p.name,
                u.is_active
            FROM teachers t
            JOIN users u
                ON t.user_id = u.id
            JOIN profiles p
                ON t.user_id = p.user_id    
            WHERE t.teacher_id = %s;
            """,
            (teacher_id,)
        )

        teacher = cursor.fetchone()

    finally:
        cursor.close()

    if teacher is None:
        raise HTTPException(
            status_code=404,
            detail="Teacher not found"
        )

    return {
        "teacher_id": teacher[0],
        "name": teacher[1],
        "is_active": teacher[2]
    }