import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from dotenv import load_dotenv

load_dotenv()

password_hash = PasswordHash.recommended()
SECRET_KEY = os.getenv("SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def authenticate_user(username: str, password: str, connection):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            u.id,
            u.username,
            u.password_hash,
            p.name
        FROM users u
        LEFT JOIN profiles p
            ON p.user_id = u.id
        WHERE u.username = %s
        AND u.is_active = TRUE;
        """,
        (username,)
    )

    user = cursor.fetchone()

    if user is None:
        cursor.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    stored_hash = user[2]

    if not password_hash.verify(password, stored_hash):
        cursor.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    cursor.execute(
        """
        SELECT r.role_name
        FROM user_roles ur
        JOIN roles r
            ON ur.role_id = r.id
        WHERE ur.user_id = %s;
        """,
        (user[0],)
    )

    roles = [row[0] for row in cursor.fetchall()]

    cursor.close()

    return {
        "user_id": user[0],
        "username": user[1],
        "name": user[3],
        "roles": roles
    }


def create_access_token(user):

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    token_data = {
        "user_id": user["user_id"],
        "username": user["username"],
        "roles": user["roles"],
        "exp": expires_at
    }

    token = jwt.encode(
        token_data,
        SECRET_KEY,
        algorithm="HS256"
    )

    return token


def verify_token(token: str = Depends(oauth2_scheme)):

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp"]}
        )

        return payload

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )