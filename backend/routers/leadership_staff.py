from fastapi import APIRouter, Depends
from backend.database import get_db
from backend.auth.dependencies import (
    require_principal,
    require_management_or_principal
)
from backend.schemas.user import UserResponse

router = APIRouter()


@router.get(
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


@router.get(
    "/management",
    response_model=list[UserResponse]
)
def get_management(
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
                AND r2.role_name = 'management'
            )
            GROUP BY
                u.id,
                u.username,
                p.name,
                u.is_active
            ORDER BY u.username;
            """
        )

        management_staff = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "username": staff[1],
            "name": staff[2],
            "is_active": staff[3],
            "roles": staff[4]
        }
        for staff in management_staff
    ]