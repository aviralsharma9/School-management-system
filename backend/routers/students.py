from fastapi import APIRouter, HTTPException, Depends
from backend.database import get_db
from backend.auth.security import password_hash
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

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM sections
            WHERE id = %s;
            """,
            (data.section_id,)
        )

        section = cursor.fetchone()

        if section is None:
            raise HTTPException(
                status_code=404,
                detail="Section not found"
            )

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = %s;
            """,
            (data.student_id,)
        )

        existing_user = cursor.fetchone()

        if existing_user is not None:
            raise HTTPException(
                status_code=400,
                detail="Student ID already exists"
            )

        hashed_password = password_hash.hash(data.password)

        cursor.execute(
            """
            INSERT INTO users
            (username, password_hash)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (
                data.student_id,
                hashed_password
            )
        )

        user_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO profiles
            (user_id, name)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (
                user_id,
                data.name
            )
        )

        profile_id = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT id
            FROM roles
            WHERE role_name = 'student';
            """
        )

        role = cursor.fetchone()

        if role is None:
            raise HTTPException(
                status_code=500,
                detail="Student role not configured"
            )

        role_id = role[0]

        cursor.execute(
            """
            INSERT INTO user_roles
            (user_id, role_id)
            VALUES (%s, %s);
            """,
            (
                user_id,
                role_id
            )
        )

        cursor.execute(
            """
            INSERT INTO students_new
            (user_id, student_id, section_id)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (
                user_id,
                data.student_id,
                data.section_id
            )
        )

        student_profile_id = cursor.fetchone()[0]

        connection.commit()

    except HTTPException:
        connection.rollback()
        raise

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()

    return {
        "message": "Student created successfully",
        "student_id": data.student_id,
        "student_profile_id": student_profile_id,
        "profile_id": profile_id,
        "user_id": user_id,
        "section_id": data.section_id
    }

@router.put("/students/{student_id}")
def update_student(
    student_id: str,
    data: StudentUpdate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                s.user_id,
                u.is_active
            FROM students_new s
            JOIN users u
                ON s.user_id = u.id
            WHERE s.student_id = %s;
            """,
            (student_id,)
        )

        student = cursor.fetchone()

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )

        user_id = student[0]
        is_active = student[1]

        if not is_active:
            raise HTTPException(
                status_code=400,
                detail="Cannot update a deactivated student"
            )

        cursor.execute(
            """
            SELECT id
            FROM sections
            WHERE id = %s;
            """,
            (data.section_id,)
        )

        section = cursor.fetchone()

        if section is None:
            raise HTTPException(
                status_code=404,
                detail="Section not found"
            )

        cursor.execute(
            """
            UPDATE profiles
            SET name = %s
            WHERE user_id = %s;
            """,
            (
                data.name,
                user_id
            )
        )

        cursor.execute(
            """
            UPDATE students_new
            SET section_id = %s
            WHERE student_id = %s;
            """,
            (
                data.section_id,
                student_id
            )
        )

        connection.commit()

    except HTTPException:
        connection.rollback()
        raise

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()

    return {
        "message": "Student updated successfully",
        "student_id": student_id,
        "name": data.name,
        "section_id": data.section_id
    }