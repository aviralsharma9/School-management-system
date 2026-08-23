from fastapi import APIRouter, HTTPException, Depends
from backend.database import get_db
from backend.auth.security import password_hash
from backend.auth.dependencies import (require_management_or_principal)
from backend.schemas.user import (
    UserCreate,
    UserResponse,
    RoleAssignment
)

router = APIRouter()

@router.post("/users/{username}/roles")
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

@router.delete("/users/{username}/roles/{role}")
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

@router.post("/users")
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

@router.get(
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

@router.get(
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

@router.delete("/users/{username}")
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
