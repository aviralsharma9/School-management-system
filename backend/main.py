from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from backend.database import get_db
from backend.auth.security import (
    authenticate_user,
    create_access_token,
    verify_token
)
from backend.auth.dependencies import require_management_or_principal
from backend.schemas.user import LoginRequest
from backend.schemas.academic import (
    SectionResponse,
    SectionCreate,
    ClassCreate,
    ClassResponse
)
from backend.routers import students, teachers, teacher_assignments, users, leadership_staff

app = FastAPI()

app.include_router(students.router)
app.include_router(teachers.router)
app.include_router(teacher_assignments.router)
app.include_router(users.router)
app.include_router(leadership_staff.router)

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
