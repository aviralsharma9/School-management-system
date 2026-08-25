from fastapi import APIRouter, HTTPException, Depends
from backend.database import get_db
from backend.auth.security import verify_token
from backend.auth.dependencies import require_management_or_principal
from backend.schemas.subject import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse
)

router = APIRouter()


@router.get(
    "/subjects",
    response_model=list[SubjectResponse]
)
def get_subjects(
    payload: dict = Depends(verify_token),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id, subject_name
            FROM subjects
            ORDER BY subject_name;
            """
        )

        subjects = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "subject_id": subject[0],
            "subject_name": subject[1]
        }
        for subject in subjects
    ]


@router.get(
    "/subjects/{subject_id}",
    response_model=SubjectResponse
)
def get_subject(
    subject_id: int,
    payload: dict = Depends(verify_token),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id, subject_name
            FROM subjects
            WHERE id = %s;
            """,
            (subject_id,)
        )

        subject = cursor.fetchone()

    finally:
        cursor.close()

    if subject is None:
        raise HTTPException(
            status_code=404,
            detail="Subject not found"
        )

    return {
        "subject_id": subject[0],
        "subject_name": subject[1]
    }


@router.post("/subjects")
def create_subject(
    data: SubjectCreate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        subject_name = data.subject_name.strip()

        if not subject_name:
            raise HTTPException(
                status_code=400,
                detail="Subject name cannot be empty"
            )

        cursor.execute(
            """
            SELECT id
            FROM subjects
            WHERE LOWER(subject_name) = LOWER(%s);
            """,
            (subject_name,)
        )

        existing_subject = cursor.fetchone()

        if existing_subject is not None:
            raise HTTPException(
                status_code=400,
                detail="Subject already exists"
            )

        cursor.execute(
            """
            INSERT INTO subjects (subject_name)
            VALUES (%s)
            RETURNING id;
            """,
            (subject_name,)
        )

        subject_id = cursor.fetchone()[0]

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
        "message": "Subject created successfully",
        "subject_id": subject_id,
        "subject_name": subject_name
    }


@router.put("/subjects/{subject_id}")
def update_subject(
    subject_id: int,
    data: SubjectUpdate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        subject_name = data.subject_name.strip()

        if not subject_name:
            raise HTTPException(
                status_code=400,
                detail="Subject name cannot be empty"
            )

        cursor.execute(
            """
            SELECT id
            FROM subjects
            WHERE id = %s;
            """,
            (subject_id,)
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
            FROM subjects
            WHERE LOWER(subject_name) = LOWER(%s)
              AND id <> %s;
            """,
            (
                subject_name,
                subject_id
            )
        )

        duplicate_subject = cursor.fetchone()

        if duplicate_subject is not None:
            raise HTTPException(
                status_code=400,
                detail="Another subject with this name already exists"
            )

        cursor.execute(
            """
            UPDATE subjects
            SET subject_name = %s
            WHERE id = %s;
            """,
            (
                subject_name,
                subject_id
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
        "message": "Subject updated successfully",
        "subject_id": subject_id,
        "subject_name": subject_name
    }


@router.delete("/subjects/{subject_id}")
def delete_subject(
    subject_id: int,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT subject_name
            FROM subjects
            WHERE id = %s;
            """,
            (subject_id,)
        )

        subject = cursor.fetchone()

        if subject is None:
            raise HTTPException(
                status_code=404,
                detail="Subject not found"
            )

        subject_name = subject[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM teacher_assignments
            WHERE subject_id = %s;
            """,
            (subject_id,)
        )

        assignment_count = cursor.fetchone()[0]

        if assignment_count > 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cannot delete a subject that is still assigned to "
                    f"{assignment_count} teacher assignment(s)"
                )
            )

        cursor.execute(
            """
            DELETE FROM subjects
            WHERE id = %s;
            """,
            (subject_id,)
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
        "message": "Subject deleted successfully",
        "subject_id": subject_id,
        "subject_name": subject_name
    }
