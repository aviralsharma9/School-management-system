from fastapi import HTTPException
from backend.auth.security import password_hash
from backend.schemas.student import StudentCreate, StudentUpdate


def create_student(data: StudentCreate, connection):

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


def update_student(student_id: str, data: StudentUpdate, connection):

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