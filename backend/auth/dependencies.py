from fastapi import HTTPException, Depends
from backend.database import get_db
from backend.auth.security import verify_token


def require_role(required_role: str):

    def role_checker(
        payload: dict = Depends(verify_token),
        connection=Depends(get_db)
    ):

        user_id = payload["user_id"]

        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                SELECT r.role_name
                FROM user_roles ur
                JOIN roles r
                    ON ur.role_id = r.id
                JOIN users u
                    ON ur.user_id = u.id
                WHERE ur.user_id = %s
                AND u.is_active = TRUE;
                """,
                (user_id,)
            )

            roles = [
                row[0]
                for row in cursor.fetchall()
            ]

        finally:
            cursor.close()

        if required_role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"{required_role} access required"
            )

        payload["roles"] = roles

        return payload

    return role_checker


def require_student(
    payload: dict = Depends(require_role("student"))
):
    return payload


def require_teacher(
    payload: dict = Depends(require_role("teacher"))
):
    return payload


def require_management(
    payload: dict = Depends(require_role("management"))
):
    return payload


def require_principal(
    payload: dict = Depends(require_role("principal"))
):
    return payload


def require_any_role(*allowed_roles):

    def role_checker(
        payload: dict = Depends(verify_token),
        connection=Depends(get_db)
    ):

        user_id = payload["user_id"]

        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                SELECT r.role_name
                FROM user_roles ur
                JOIN roles r
                    ON ur.role_id = r.id
                JOIN users u
                    ON ur.user_id = u.id
                WHERE ur.user_id = %s
                AND u.is_active = TRUE;
                """,
                (user_id,)
            )

            roles = [
                row[0]
                for row in cursor.fetchall()
            ]

        finally:
            cursor.close()

        if not any(
            role in allowed_roles
            for role in roles
        ):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource"
            )

        payload["roles"] = roles

        return payload

    return role_checker


def require_management_or_principal(
    payload: dict = Depends(
        require_any_role(
            "management",
            "principal"
        )
    )
):
    return payload