from pydantic import BaseModel

class StudentCreate(BaseModel):
    student_id: str
    name: str
    section_id: int
    password: str

class StudentProfileResponse(BaseModel):
    student_id: str
    name: str
    class_name: str
    section_name: str
    is_active: bool

class StudentManagementResponse(BaseModel):
    student_id: str
    name: str
    class_name: str
    section_name: str
    is_active: bool

class StudentUpdate(BaseModel):
    name: str
    section_id: int