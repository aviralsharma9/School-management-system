from pydantic import BaseModel

class TeacherCreate(BaseModel):
    teacher_id: str
    name: str
    password: str

class TeacherUpdate(BaseModel):
    name: str

class TeacherProfileResponse(BaseModel):
    teacher_id: str
    name: str
    is_active: bool