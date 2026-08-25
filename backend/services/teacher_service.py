from fastapi import HTTPException
from backend.auth.security import password_hash
from backend.schemas.teacher import TeacherCreate, TeacherUpdate


def create_teacher(data: TeacherCreate, connection):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = %s;
            """,
            (data.teacher_id,)
        )

        existing_user = cursor.fetchone()

        if existing_user is not None:
            raise HTTPException(
                status_code=400,
                detail="Teacher ID already exists"
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
                data.teacher_id,
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
            WHERE role_name = 'teacher';
            """
        )

        role = cursor.fetchone()

        if role is None:
            raise HTTPException(
                status_code=500,
                detail="Teacher role not configured"
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
            INSERT INTO teachers
            (user_id, teacher_id)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (
                user_id,
                data.teacher_id
            )
        )

        teacher_profile_id = cursor.fetchone()[0]

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
        "message": "Teacher created successfully",
        "teacher_id": data.teacher_id,
        "teacher_profile_id": teacher_profile_id,
        "profile_id": profile_id,
        "user_id": user_id
    }


def update_teacher(teacher_id: str, data: TeacherUpdate, connection):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                t.user_id,
                u.is_active
            FROM teachers t
            JOIN users u
                ON t.user_id = u.id
            WHERE t.teacher_id = %s;
            """,
            (teacher_id,)
        )

        teacher = cursor.fetchone()

        if teacher is None:
            raise HTTPException(
                status_code=404,
                detail="Teacher not found"
            )

        user_id = teacher[0]
        is_active = teacher[1]

        if not is_active:
            raise HTTPException(
                status_code=400,
                detail="Cannot update a deactivated teacher"
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
        "message": "Teacher updated successfully",
        "teacher_id": teacher_id,
        "name": data.name
    }