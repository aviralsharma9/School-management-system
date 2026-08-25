from fastapi import APIRouter, HTTPException, Depends
from backend.database import get_db
from backend.auth.dependencies import (
    require_student,
    require_management_or_principal
)
from backend.schemas.student import (
    StudentCreate,
    StudentProfileResponse,
    StudentManagementResponse,
    StudentUpdate
)
from backend.services import student_service

router = APIRouter()

@router.get(
    "/students",
    response_model=list[StudentProfileResponse]
)
def get_students(
    payload: dict = Depends(require_management_or_principal),
    connection = Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                s.student_id,
                p.name,
                c.class_name,
                sec.section_name,
                u.is_active
            FROM students_new s
            JOIN profiles p
                ON s.user_id = p.user_id
            JOIN users u
                ON s.user_id = u.id
            JOIN sections sec
                ON s.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            WHERE u.is_active = TRUE
            ORDER BY c.class_name::INTEGER, sec.section_name, s.student_id;
            """
        )

        students = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "student_id": student[0],
            "name": student[1],
            "class_name": student[2],
            "section_name": student[3],
            "is_active": student[4]
        }
        for student in students
    ]

@router.get(
    "/students/me",
    response_model=StudentProfileResponse
)
def get_my_profile(
    payload: dict = Depends(require_student),
    connection=Depends(get_db)
):

    user_id = payload["user_id"]

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                s.student_id,
                p.name,
                c.class_name,
                sec.section_name,
                u.is_active
            FROM students_new s
            JOIN users u
                ON s.user_id = u.id
            JOIN profiles p
                ON s.user_id = p.user_id
            JOIN sections sec
                ON s.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            WHERE s.user_id = %s;
            """,
            (user_id,)
        )

        student = cursor.fetchone()

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student profile not found"
            )

    finally:
        cursor.close()

    return {
        "student_id": student[0],
        "name": student[1],
        "class_name": student[2],
        "section_name": student[3],
        "is_active": student[4]
    }

@router.get(
    "/students/deactivated",
    response_model=list[StudentProfileResponse]
)
def get_deactivated_students(
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                s.student_id,
                p.name,
                c.class_name,
                sec.section_name,
                u.is_active
            FROM students_new s
            JOIN users u
                ON s.user_id = u.id
            JOIN profiles p
                ON s.user_id = p.user_id    
            JOIN sections sec
                ON s.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            WHERE u.is_active = FALSE
            ORDER BY c.class_name::INTEGER,
                     sec.section_name,
                     s.student_id;
            """
        )

        students = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "student_id": student[0],
            "name": student[1],
            "class_name": student[2],
            "section_name": student[3],
            "is_active": student[4]
        }
        for student in students
    ]

@router.get(
    "/students/{student_id}",
    response_model=StudentManagementResponse
)
def get_student(
    student_id: str,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                s.student_id,
                p.name,
                c.class_name,
                sec.section_name,
                u.is_active
            FROM students_new s
            JOIN users u
                ON s.user_id = u.id
            JOIN profiles p
                ON s.user_id = p.user_id    
            JOIN sections sec
                ON s.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            WHERE s.student_id = %s;
            """,
            (student_id,)
        )

        student = cursor.fetchone()

    finally:
        cursor.close()

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return {
        "student_id": student[0],
        "name": student[1],
        "class_name": student[2],
        "section_name": student[3],
        "is_active": student[4]
    }

@router.post("/students")
def create_student(
    data: StudentCreate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):
    return student_service.create_student(data, connection)
 
 
@router.put("/students/{student_id}")
def update_student(
    student_id: str,
    data: StudentUpdate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):
    return student_service.update_student(student_id, data, connection)