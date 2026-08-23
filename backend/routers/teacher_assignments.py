from fastapi import APIRouter, HTTPException, Depends
from backend.database import get_db
from backend.auth.dependencies import require_management_or_principal
from backend.schemas.assignment import (
    TeacherAssignmentCreate,
    TeacherAssignmentResponse,
    TeacherAssignmentUpdate
)

router = APIRouter()

@router.post("/teacher-assignments")
def create_teacher_assignment(
    data: TeacherAssignmentCreate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT t.id
            FROM teachers t
            JOIN users u
                ON t.user_id = u.id
            WHERE t.id = %s
            AND u.is_active = TRUE;
            """,
            (data.teacher_id,)
        )

        teacher = cursor.fetchone()

        if teacher is None:
            raise HTTPException(
                status_code=404,
                detail="Active teacher not found"
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
            SELECT id
            FROM subjects
            WHERE id = %s;
            """,
            (data.subject_id,)
        )

        subject = cursor.fetchone()

        if subject is None:
            raise HTTPException(
                status_code=404,
                detail="Subject not found"
            )

        cursor.execute(
            """
            SELECT id
            FROM teacher_assignments
            WHERE teacher_id = %s
            AND section_id = %s
            AND subject_id = %s;
            """,
            (
                data.teacher_id,
                data.section_id,
                data.subject_id
            )
        )

        existing_assignment = cursor.fetchone()

        if existing_assignment is not None:
            raise HTTPException(
                status_code=400,
                detail="This teacher assignment already exists"
            )

        cursor.execute(
            """
            INSERT INTO teacher_assignments
            (teacher_id, section_id, subject_id)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (
                data.teacher_id,
                data.section_id,
                data.subject_id
            )
        )

        assignment_id = cursor.fetchone()[0]

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
        "message": "Teacher assigned successfully",
        "assignment_id": assignment_id,
        "teacher_id": data.teacher_id,
        "section_id": data.section_id,
        "subject_id": data.subject_id
    }

@router.get(
    "/teacher-assignments",
    response_model=list[TeacherAssignmentResponse]
)
def get_teacher_assignments(
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                ta.id,
                t.teacher_id,
                p.name,
                c.class_name,
                sec.section_name,
                sub.subject_name,
                u.is_active
            FROM teacher_assignments ta
            JOIN teachers t
                ON ta.teacher_id = t.id
            JOIN users u
                ON t.user_id = u.id  
            JOIN profiles p
                ON t.user_id = p.user_id      
            JOIN sections sec
                ON ta.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            JOIN subjects sub
                ON ta.subject_id = sub.id
            WHERE u.is_active = TRUE    
            ORDER BY
                c.class_name::INTEGER,
                sec.section_name,
                t.teacher_id,
                sub.subject_name;
            """
        )

        assignments = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "assignment_id": assignment[0],
            "teacher_id": assignment[1],
            "teacher_name": assignment[2],
            "class_name": assignment[3],
            "section_name": assignment[4],
            "subject_name": assignment[5],
            "is_active": assignment[6]
        }
        for assignment in assignments
    ]

@router.get(
    "/teacher-assignments/{teacher_id}",
    response_model=list[TeacherAssignmentResponse]
)
def get_teacher_assignments_by_teacher(
    teacher_id: str,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                ta.id,
                t.teacher_id,
                p.name,
                c.class_name,
                sec.section_name,
                sub.subject_name,
                u.is_active
            FROM teacher_assignments ta
            JOIN teachers t
                ON ta.teacher_id = t.id
            JOIN users u
                ON t.user_id = u.id
            JOIN profiles p
                ON t.user_id = p.user_id
            JOIN sections sec
                ON ta.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            JOIN subjects sub
                ON ta.subject_id = sub.id
            WHERE t.teacher_id = %s
            AND u.is_active = TRUE
            ORDER BY
                c.class_name::INTEGER,
                sec.section_name,
                sub.subject_name;
            """,
            (teacher_id,)
        )

        assignments = cursor.fetchall()

    finally:
        cursor.close()

    if not assignments:
        raise HTTPException(
            status_code=404,
            detail="No active assignments found for this teacher"
        )

    return [
        {
            "assignment_id": assignment[0],
            "teacher_id": assignment[1],
            "teacher_name": assignment[2],
            "class_name": assignment[3],
            "section_name": assignment[4],
            "subject_name": assignment[5],
            "is_active": assignment[6]
        }
        for assignment in assignments
    ]

@router.delete("/teacher-assignments/{assignment_id}")
def delete_teacher_assignment(
    assignment_id: int,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM teacher_assignments
            WHERE id = %s;
            """,
            (assignment_id,)
        )

        assignment = cursor.fetchone()

        if assignment is None:
            raise HTTPException(
                status_code=404,
                detail="Teacher assignment not found"
            )

        cursor.execute(
            """
            DELETE FROM teacher_assignments
            WHERE id = %s;
            """,
            (assignment_id,)
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
        "message": "Teacher assignment deleted successfully",
        "assignment_id": assignment_id
    }

@router.put("/teacher-assignments/{assignment_id}")
def update_teacher_assignment(
    assignment_id: int,
    data: TeacherAssignmentUpdate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM teacher_assignments
            WHERE id = %s;
            """,
            (assignment_id,)
        )

        assignment = cursor.fetchone()

        if assignment is None:
            raise HTTPException(
                status_code=404,
                detail="Teacher assignment not found"
            )

        cursor.execute(
            """
            SELECT t.id
            FROM teachers t
            JOIN users u
                ON t.user_id = u.id
            WHERE t.id = %s
            AND u.is_active = TRUE;
            """,
            (data.teacher_id,)
        )

        teacher = cursor.fetchone()

        if teacher is None:
            raise HTTPException(
                status_code=404,
                detail="Active teacher not found"
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
            SELECT id
            FROM subjects
            WHERE id = %s;
            """,
            (data.subject_id,)
        )

        subject = cursor.fetchone()

        if subject is None:
            raise HTTPException(
                status_code=404,
                detail="Subject not found"
            )
        
        cursor.execute(
            """
            SELECT id
            FROM teacher_assignments
            WHERE teacher_id = %s
            AND section_id = %s
            AND subject_id = %s
            AND id != %s;
            """,
            (
                data.teacher_id,
                data.section_id,
                data.subject_id,
                assignment_id
            )
        )

        duplicate = cursor.fetchone()

        if duplicate is not None:
            raise HTTPException(
                status_code=400,
                detail="This teacher assignment already exists"
            )

        cursor.execute(
            """
            UPDATE teacher_assignments
            SET teacher_id = %s,
                section_id = %s,
                subject_id = %s
            WHERE id = %s;
            """,
            (
                data.teacher_id,
                data.section_id,
                data.subject_id,
                assignment_id
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
        "message": "Teacher assignment updated successfully",
        "assignment_id": assignment_id,
        "teacher_id": data.teacher_id,
        "section_id": data.section_id,
        "subject_id": data.subject_id
    }