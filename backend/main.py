from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import psycopg
from backend.database import get_db
from backend.auth.security import (
    password_hash,
    authenticate_user,
    create_access_token,
    verify_token
)
from backend.auth.dependencies import (
    require_student,
    require_teacher,
    require_management,
    require_principal,
    require_any_role,
    require_management_or_principal
)

from backend.schemas.user import (
    LoginRequest,
    UserCreate,
    UserResponse,
    RoleAssignment
)

from backend.schemas.academic import (
    SectionResponse,
    SectionCreate,
    ClassCreate,
    ClassResponse
)

from backend.routers import students, teachers, teacher_assignments

app = FastAPI()
app.include_router(students.router)
app.include_router(teachers.router)
app.include_router(teacher_assignments.router)


# ------------ENDPOINTS-------------

@app.get("/verify-token")
def verify_my_token(payload: dict = Depends(verify_token)):

    return {
        "message": "Token is valid",
        "payload": payload
    }

#-------------login(json)----------------

@app.post("/login")
def login(
    data: LoginRequest,
    connection=Depends(get_db)
):

    user = authenticate_user(
        data.username,
        data.password,
        connection
    )

    token = create_access_token(user)

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "roles": user["roles"]
    }

#-------Login throuth request form---------

@app.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    connection=Depends(get_db)
):

    user = authenticate_user(
        form_data.username,
        form_data.password,
        connection
    )

    token = create_access_token(user)

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@app.get("/")
def home():
    return {
        "message": "School Management System API is running!"
    }

@app.get("/sections", response_model=list[SectionResponse])
def get_sections(
    payload: dict = Depends(verify_token),
    connection=Depends(get_db)):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            sections.id,
            classes.class_name,
            sections.section_name
        FROM sections
        JOIN classes
            ON sections.class_id = classes.id
        ORDER BY classes.class_name::INTEGER, sections.section_name;
        """
    )

    sections = cursor.fetchall()

    cursor.close()

    return [
        {
            "section_id": section[0],
            "class_name": section[1],
            "section_name": section[2]
        }
        for section in sections
    ]

@app.post("/sections")
def create_section(
    data: SectionCreate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            "SELECT id FROM classes WHERE id = %s;",
            (data.class_id,)
        )

        class_exists = cursor.fetchone()

        if class_exists is None:
            cursor.close()

            raise HTTPException(
                status_code=404,
                detail="Class not found"
            )

    
        cursor.execute(
            """
            INSERT INTO sections
            (class_id, section_name)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (
                data.class_id,
                data.section_name
            )
        )

        section_id = cursor.fetchone()[0]

        connection.commit()

    except Exception:
        connection.rollback()
        raise
    
    finally:
        cursor.close()

    return {
        "message": "Section created successfully",
        "section_id": section_id,
        "class_id": data.class_id,
        "section_name": data.section_name
    }

@app.get("/classes", response_model=list[ClassResponse])
def get_classes(
    payload: dict = Depends(verify_token),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id, class_name
            FROM classes
            ORDER BY class_name::INTEGER;
            """
        )

        classes = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "class_id": class_item[0],
            "class_name": class_item[1]
        }
        for class_item in classes
    ]

@app.post("/classes")
def create_class(
    data: ClassCreate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM classes
            WHERE class_name = %s;
            """,
            (data.class_name,)
        )

        existing_class = cursor.fetchone()

        if existing_class is not None:
            cursor.close()

            raise HTTPException(
                status_code=400,
                detail="Class already exists"
            )


        cursor.execute(
            """
            INSERT INTO classes (class_name)
            VALUES (%s)
            RETURNING id;
            """,
            (data.class_name,)
        )

        class_id = cursor.fetchone()[0]

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()

    return {
        "message": "Class created successfully",
        "class_id": class_id,
        "class_name": data.class_name
    }

@app.post("/users/{username}/roles")
def assign_user_role(
    username: str,
    data: RoleAssignment,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        requester_roles = payload.get("roles", [])

        requested_role = data.role.lower()

        allowed_roles = {
            "student",
            "teacher",
            "management",
            "principal"
        }

        if requested_role not in allowed_roles:
            raise HTTPException(
                status_code=400,
                detail="Invalid role"
            )

        if "principal" in requester_roles:
            pass

        elif "management" in requester_roles:

            if requested_role in ["management", "principal"]:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Management can assign only lower-level roles. "
                        "Principal or management role cannot be assigned."
                    )
                )

        else:
            raise HTTPException(
                status_code=403,
                detail="Management or principal role required"
            )

        cursor.execute(
            """
            SELECT id, is_active
            FROM users
            WHERE username = %s;
            """,
            (username,)
        )

        user = cursor.fetchone()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        user_id = user[0]
        is_active = user[1]

        if not is_active:
            raise HTTPException(
                status_code=400,
                detail="User account is inactive"
            )

        cursor.execute(
            """
            SELECT id
            FROM roles
            WHERE role_name = %s;
            """,
            (requested_role,)
        )

        role = cursor.fetchone()

        if role is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid role"
            )

        role_id = role[0]

        cursor.execute(
            """
            SELECT 1
            FROM user_roles
            WHERE user_id = %s
            AND role_id = %s;
            """,
            (
                user_id,
                role_id
            )
        )

        existing_role = cursor.fetchone()

        if existing_role is not None:
            raise HTTPException(
                status_code=400,
                detail=f"User already has {requested_role} role"
            )

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
        "message": "Role assigned successfully",
        "username": username,
        "role": requested_role
    }

@app.delete("/users/{username}/roles/{role}")
def remove_user_role(
    username: str,
    role: str,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        requester_roles = payload.get("roles", [])

        requested_role = role.lower()

        allowed_roles = {
            "student",
            "teacher",
            "management",
            "principal"
        }

        if requested_role not in allowed_roles:
            raise HTTPException(
                status_code=400,
                detail="Invalid role"
            )

        if "principal" in requester_roles:
            pass

        elif "management" in requester_roles:

            if requested_role in ["management", "principal"]:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Management cannot remove "
                        "management or principal role"
                    )
                )

        else:
            raise HTTPException(
                status_code=403,
                detail="Management or principal role required"
            )

        cursor.execute(
            """
            SELECT id, is_active
            FROM users
            WHERE username = %s;
            """,
            (username,)
        )

        user = cursor.fetchone()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        user_id = user[0]

        if not user[1]:
            raise HTTPException(
                status_code=400,
                detail="User account is inactive"
            )

        cursor.execute(
            """
            SELECT id
            FROM roles
            WHERE role_name = %s;
            """,
            (requested_role,)
        )

        role_record = cursor.fetchone()

        if role_record is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid role"
            )

        role_id = role_record[0]

        cursor.execute(
            """
            SELECT 1
            FROM user_roles
            WHERE user_id = %s
            AND role_id = %s;
            """,
            (
                user_id,
                role_id
            )
        )

        existing_role = cursor.fetchone()

        if existing_role is None:
            raise HTTPException(
                status_code=400,
                detail=f"User does not have {requested_role} role"
            )

        if requested_role == "principal":

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM user_roles ur
                JOIN roles r
                    ON ur.role_id = r.id
                JOIN users u
                    ON ur.user_id = u.id
                WHERE r.role_name = 'principal'
                AND u.is_active = TRUE;
                """
            )

            principal_count = cursor.fetchone()[0]

            if principal_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot remove the last active principal"
                )

        cursor.execute(
            """
            DELETE FROM user_roles
            WHERE user_id = %s
            AND role_id = %s;
            """,
            (
                user_id,
                role_id
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
        "message": "Role removed successfully",
        "username": username,
        "removed_role": requested_role
    }

@app.post("/users")
def create_user(
    data: UserCreate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = %s;
            """,
            (data.username,)
        )

        existing_user = cursor.fetchone()

        if existing_user is not None:
            raise HTTPException(
                status_code=400,
                detail="Username already exists"
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
                data.username,
                hashed_password
            )
        )

        user_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO profiles
            (user_id, name)
            VALUES (%s, %s);
            """,
            (
                user_id,
                data.name
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
        "message": "User created successfully",
        "user_id": user_id,
        "username": data.username,
        "name": data.name
    }

@app.get(
    "/users",
    response_model=list[UserResponse]
)
def get_users(
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                u.id,
                u.username,
                p.name,
                u.is_active,
                COALESCE(
                    ARRAY_AGG(r.role_name)
                    FILTER (WHERE r.role_name IS NOT NULL),
                    '{}'
                ) AS roles
            FROM users u
            JOIN profiles p
                ON u.id = p.user_id
            LEFT JOIN user_roles ur
                ON u.id = ur.user_id
            LEFT JOIN roles r
                ON ur.role_id = r.id
            GROUP BY
                u.id,
                u.username,
                p.name,
                u.is_active
            ORDER BY u.username;
            """
        )

        users = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "username": user[1],
            "name": user[2],
            "is_active": user[3],
            "roles": user[4]
        }
        for user in users
    ]

@app.get(
    "/users/{username}",
    response_model=UserResponse
)
def get_user_by_username(
    username: str,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                u.id,
                u.username,
                p.name,
                u.is_active,
                COALESCE(
                    ARRAY_AGG(r.role_name)
                    FILTER (WHERE r.role_name IS NOT NULL),
                    '{}'
                ) AS roles
            FROM users u
            JOIN profiles p
                ON u.id = p.user_id
            LEFT JOIN user_roles ur
                ON u.id = ur.user_id
            LEFT JOIN roles r
                ON ur.role_id = r.id
            WHERE u.username = %s
            GROUP BY
                u.id,
                u.username,
                p.name,
                u.is_active;
            """,
            (username,)
        )

        user = cursor.fetchone()

    finally:
        cursor.close()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "username": user[1],
        "name": user[2],
        "is_active": user[3],
        "roles": user[4]
    }

@app.delete("/users/{username}")
def deactivate_user(
    username: str,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id, is_active
            FROM users
            WHERE username = %s;
            """,
            (username,)
        )

        user = cursor.fetchone()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        user_id = user[0]

        cursor.execute(
            """
            SELECT r.role_name
            FROM user_roles ur
            JOIN roles r
                ON ur.role_id = r.id
            WHERE ur.user_id = %s;
            """,
            (user_id,)
        )

        target_roles = [
            row[0]
            for row in cursor.fetchall()
        ]

        requester_roles = payload.get("roles", [])

        if "management" in requester_roles:
            if (
                "principal" in target_roles
                or "management" in target_roles
            ):
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Management cannot deactivate "
                        "principal or management users"
                    )
                )

        cursor.execute(
            """
            UPDATE users
            SET is_active = FALSE
            WHERE id = %s;
            """,
            (user_id,)
        )

        connection.commit()

    except HTTPException:
        connection.rollback()
        raise

    except Exception:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to deactivate user"
        )

    finally:
        cursor.close()

    return {
        "message": "User deactivated successfully",
        "username": username,
        "is_active": False,
        "roles": target_roles
    }

@app.get(
    "/principals",
    response_model=list[UserResponse]
)
def get_principals(
    payload: dict = Depends(require_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                u.id,
                u.username,
                p.name,
                u.is_active,
                ARRAY_AGG(r.role_name ORDER BY r.role_name) AS roles
            FROM users u
            JOIN profiles p
                ON u.id = p.user_id
            JOIN user_roles ur
                ON u.id = ur.user_id
            JOIN roles r
                ON ur.role_id = r.id
            WHERE u.is_active = TRUE
            AND EXISTS (
                SELECT 1
                FROM user_roles ur2
                JOIN roles r2
                    ON ur2.role_id = r2.id
                WHERE ur2.user_id = u.id
                AND r2.role_name = 'principal'
            )
            GROUP BY
                u.id,
                u.username,
                p.name,
                u.is_active
            ORDER BY u.username;
            """
        )

        principals = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "username": principal[1],
            "name": principal[2],
            "is_active": principal[3],
            "roles": principal[4]
        }
        for principal in principals
    ]

