from pydantic import BaseModel

class TeacherAssignmentCreate(BaseModel):
    teacher_id: int
    section_id: int
    subject_id: int

class TeacherAssignmentResponse(BaseModel):
    assignment_id: int
    teacher_id: str
    teacher_name: str
    class_name: str
    section_name: str
    subject_name: str
    is_active: bool

class TeacherAssignmentUpdate(BaseModel):
    teacher_id: int
    section_id: int
    subject_id: int