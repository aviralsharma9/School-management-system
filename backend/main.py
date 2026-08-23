from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordRequestForm
from backend.database import get_db
from backend.auth.security import (
    authenticate_user,
    create_access_token,
    verify_token
)
from backend.schemas.user import LoginRequest
from backend.routers import (
    students,
    teachers,
    teacher_assignments,
    users,
    leadership_staff,
    academic
)

app = FastAPI()

app.include_router(students.router)
app.include_router(teachers.router)
app.include_router(teacher_assignments.router)
app.include_router(users.router)
app.include_router(leadership_staff.router)
app.include_router(academic.router)

# ------------verify-token-------------

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