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
from backend.schemas.student import (
    StudentCreate,
    StudentProfileResponse,
    StudentManagementResponse,
    StudentUpdate
)
from backend.schemas.teacher import (
    TeacherCreate,
    TeacherUpdate,
    TeacherProfileResponse
)
from backend.schemas.academic import (
    SectionResponse,
    SectionCreate,
    ClassCreate,
    ClassResponse
)
from backend.schemas.assignment import (
    TeacherAssignmentCreate,
    TeacherAssignmentResponse,
    TeacherAssignmentUpdate
)

app = FastAPI()


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

@app.get(
    "/students",
    response_model=list[StudentProfileResponse]
)
def get_students(
    payload: dict = Depends(require_management_or_principal),
    connection = Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                s.student_id,
                p.name,
                c.class_name,
                sec.section_name,
                u.is_active
            FROM students_new s
            JOIN profiles p
                ON s.user_id = p.user_id
            JOIN users u
                ON s.user_id = u.id
            JOIN sections sec
                ON s.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            WHERE u.is_active = TRUE
            ORDER BY c.class_name::INTEGER, sec.section_name, s.student_id;
            """
        )

        students = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "student_id": student[0],
            "name": student[1],
            "class_name": student[2],
            "section_name": student[3],
            "is_active": student[4]
        }
        for student in students
    ]

@app.get(
    "/students/me",
    response_model=StudentProfileResponse
)
def get_my_profile(
    payload: dict = Depends(require_student),
    connection=Depends(get_db)
):

    user_id = payload["user_id"]

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                s.student_id,
                p.name,
                c.class_name,
                sec.section_name,
                u.is_active
            FROM students_new s
            JOIN users u
                ON s.user_id = u.id
            JOIN profiles p
                ON s.user_id = p.user_id
            JOIN sections sec
                ON s.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            WHERE s.user_id = %s;
            """,
            (user_id,)
        )

        student = cursor.fetchone()

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student profile not found"
            )

    finally:
        cursor.close()

    return {
        "student_id": student[0],
        "name": student[1],
        "class_name": student[2],
        "section_name": student[3],
        "is_active": student[4]
    }

@app.get(
    "/students/deactivated",
    response_model=list[StudentProfileResponse]
)
def get_deactivated_students(
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                s.student_id,
                p.name,
                c.class_name,
                sec.section_name,
                u.is_active
            FROM students_new s
            JOIN users u
                ON s.user_id = u.id
            JOIN profiles p
                ON s.user_id = p.user_id    
            JOIN sections sec
                ON s.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            WHERE u.is_active = FALSE
            ORDER BY c.class_name::INTEGER,
                     sec.section_name,
                     s.student_id;
            """
        )

        students = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "student_id": student[0],
            "name": student[1],
            "class_name": student[2],
            "section_name": student[3],
            "is_active": student[4]
        }
        for student in students
    ]

@app.get(
    "/students/{student_id}",
    response_model=StudentManagementResponse
)
def get_student(
    student_id: str,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                s.student_id,
                p.name,
                c.class_name,
                sec.section_name,
                u.is_active
            FROM students_new s
            JOIN users u
                ON s.user_id = u.id
            JOIN profiles p
                ON s.user_id = p.user_id    
            JOIN sections sec
                ON s.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            WHERE s.student_id = %s;
            """,
            (student_id,)
        )

        student = cursor.fetchone()

    finally:
        cursor.close()

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return {
        "student_id": student[0],
        "name": student[1],
        "class_name": student[2],
        "section_name": student[3],
        "is_active": student[4]
    }

@app.post("/students")
def create_student(
    data: StudentCreate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

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

@app.put("/students/{student_id}")
def update_student(
    student_id: str,
    data: StudentUpdate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

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

@app.post("/teachers")
def create_teacher(
    data: TeacherCreate,
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

@app.put("/teachers/{teacher_id}")
def update_teacher(
    teacher_id: str,
    data: TeacherUpdate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

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

@app.get(
    "/teachers/deactivated",
    response_model=list[TeacherProfileResponse]
)
def get_deactivated_teachers(
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                t.teacher_id,
                p.name,
                u.is_active
            FROM teachers t
            JOIN users u
                ON t.user_id = u.id
            JOIN profiles p
                ON t.user_id = p.user_id    
            WHERE u.is_active = FALSE
            ORDER BY t.teacher_id;
            """
        )

        teachers = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "teacher_id": teacher[0],
            "name": teacher[1],
            "is_active": teacher[2]
        }
        for teacher in teachers
    ]

@app.get(
    "/teachers",
    response_model=list[TeacherProfileResponse]
)
def get_teachers(
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                t.teacher_id,
                p.name,
                u.is_active
            FROM teachers t
            JOIN users u
                ON t.user_id = u.id
            JOIN profiles p
                ON t.user_id = p.user_id    
            WHERE u.is_active = TRUE
            ORDER BY t.teacher_id;
            """
        )

        teachers = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "teacher_id": teacher[0],
            "name": teacher[1],
            "is_active": teacher[2]
        }
        for teacher in teachers
    ]

@app.get(
    "/teachers/{teacher_id}",
    response_model=TeacherProfileResponse
)
def get_teacher(
    teacher_id: str,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                t.teacher_id,
                p.name,
                u.is_active
            FROM teachers t
            JOIN users u
                ON t.user_id = u.id
            JOIN profiles p
                ON t.user_id = p.user_id    
            WHERE t.teacher_id = %s;
            """,
            (teacher_id,)
        )

        teacher = cursor.fetchone()

    finally:
        cursor.close()

    if teacher is None:
        raise HTTPException(
            status_code=404,
            detail="Teacher not found"
        )

    return {
        "teacher_id": teacher[0],
        "name": teacher[1],
        "is_active": teacher[2]
    }

@app.post("/teacher-assignments")
def create_teacher_assignment(
    data: TeacherAssignmentCreate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT t.id
            FROM teachers t
            JOIN users u
                ON t.user_id = u.id
            WHERE t.id = %s
            AND u.is_active = TRUE;
            """,
            (data.teacher_id,)
        )

        teacher = cursor.fetchone()

        if teacher is None:
            raise HTTPException(
                status_code=404,
                detail="Active teacher not found"
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
            SELECT id
            FROM subjects
            WHERE id = %s;
            """,
            (data.subject_id,)
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
            FROM teacher_assignments
            WHERE teacher_id = %s
            AND section_id = %s
            AND subject_id = %s;
            """,
            (
                data.teacher_id,
                data.section_id,
                data.subject_id
            )
        )

        existing_assignment = cursor.fetchone()

        if existing_assignment is not None:
            raise HTTPException(
                status_code=400,
                detail="This teacher assignment already exists"
            )

        cursor.execute(
            """
            INSERT INTO teacher_assignments
            (teacher_id, section_id, subject_id)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (
                data.teacher_id,
                data.section_id,
                data.subject_id
            )
        )

        assignment_id = cursor.fetchone()[0]

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
        "message": "Teacher assigned successfully",
        "assignment_id": assignment_id,
        "teacher_id": data.teacher_id,
        "section_id": data.section_id,
        "subject_id": data.subject_id
    }
@app.get(
    "/teacher-assignments",
    response_model=list[TeacherAssignmentResponse]
)
def get_teacher_assignments(
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                ta.id,
                t.teacher_id,
                p.name,
                c.class_name,
                sec.section_name,
                sub.subject_name,
                u.is_active
            FROM teacher_assignments ta
            JOIN teachers t
                ON ta.teacher_id = t.id
            JOIN users u
                ON t.user_id = u.id  
            JOIN profiles p
                ON t.user_id = p.user_id      
            JOIN sections sec
                ON ta.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            JOIN subjects sub
                ON ta.subject_id = sub.id
            WHERE u.is_active = TRUE    
            ORDER BY
                c.class_name::INTEGER,
                sec.section_name,
                t.teacher_id,
                sub.subject_name;
            """
        )

        assignments = cursor.fetchall()

    finally:
        cursor.close()

    return [
        {
            "assignment_id": assignment[0],
            "teacher_id": assignment[1],
            "teacher_name": assignment[2],
            "class_name": assignment[3],
            "section_name": assignment[4],
            "subject_name": assignment[5],
            "is_active": assignment[6]
        }
        for assignment in assignments
    ]

@app.get(
    "/teacher-assignments/{teacher_id}",
    response_model=list[TeacherAssignmentResponse]
)
def get_teacher_assignments_by_teacher(
    teacher_id: str,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                ta.id,
                t.teacher_id,
                p.name,
                c.class_name,
                sec.section_name,
                sub.subject_name,
                u.is_active
            FROM teacher_assignments ta
            JOIN teachers t
                ON ta.teacher_id = t.id
            JOIN users u
                ON t.user_id = u.id
            JOIN profiles p
                ON t.user_id = p.user_id
            JOIN sections sec
                ON ta.section_id = sec.id
            JOIN classes c
                ON sec.class_id = c.id
            JOIN subjects sub
                ON ta.subject_id = sub.id
            WHERE t.teacher_id = %s
            AND u.is_active = TRUE
            ORDER BY
                c.class_name::INTEGER,
                sec.section_name,
                sub.subject_name;
            """,
            (teacher_id,)
        )

        assignments = cursor.fetchall()

    finally:
        cursor.close()

    if not assignments:
        raise HTTPException(
            status_code=404,
            detail="No active assignments found for this teacher"
        )

    return [
        {
            "assignment_id": assignment[0],
            "teacher_id": assignment[1],
            "teacher_name": assignment[2],
            "class_name": assignment[3],
            "section_name": assignment[4],
            "subject_name": assignment[5],
            "is_active": assignment[6]
        }
        for assignment in assignments
    ]

@app.delete("/teacher-assignments/{assignment_id}")
def delete_teacher_assignment(
    assignment_id: int,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM teacher_assignments
            WHERE id = %s;
            """,
            (assignment_id,)
        )

        assignment = cursor.fetchone()

        if assignment is None:
            raise HTTPException(
                status_code=404,
                detail="Teacher assignment not found"
            )

        cursor.execute(
            """
            DELETE FROM teacher_assignments
            WHERE id = %s;
            """,
            (assignment_id,)
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
        "message": "Teacher assignment deleted successfully",
        "assignment_id": assignment_id
    }

@app.put("/teacher-assignments/{assignment_id}")
def update_teacher_assignment(
    assignment_id: int,
    data: TeacherAssignmentUpdate,
    payload: dict = Depends(require_management_or_principal),
    connection=Depends(get_db)
):

    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM teacher_assignments
            WHERE id = %s;
            """,
            (assignment_id,)
        )

        assignment = cursor.fetchone()

        if assignment is None:
            raise HTTPException(
                status_code=404,
                detail="Teacher assignment not found"
            )

        cursor.execute(
            """
            SELECT t.id
            FROM teachers t
            JOIN users u
                ON t.user_id = u.id
            WHERE t.id = %s
            AND u.is_active = TRUE;
            """,
            (data.teacher_id,)
        )

        teacher = cursor.fetchone()

        if teacher is None:
            raise HTTPException(
                status_code=404,
                detail="Active teacher not found"
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
            SELECT id
            FROM subjects
            WHERE id = %s;
            """,
            (data.subject_id,)
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
            FROM teacher_assignments
            WHERE teacher_id = %s
            AND section_id = %s
            AND subject_id = %s
            AND id != %s;
            """,
            (
                data.teacher_id,
                data.section_id,
                data.subject_id,
                assignment_id
            )
        )

        duplicate = cursor.fetchone()

        if duplicate is not None:
            raise HTTPException(
                status_code=400,
                detail="This teacher assignment already exists"
            )

        cursor.execute(
            """
            UPDATE teacher_assignments
            SET teacher_id = %s,
                section_id = %s,
                subject_id = %s
            WHERE id = %s;
            """,
            (
                data.teacher_id,
                data.section_id,
                data.subject_id,
                assignment_id
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
        "message": "Teacher assignment updated successfully",
        "assignment_id": assignment_id,
        "teacher_id": data.teacher_id,
        "section_id": data.section_id,
        "subject_id": data.subject_id
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

