from pydantic import BaseModel

class SubjectCreate(BaseModel):
    subject_name: str

class SubjectUpdate(BaseModel):
    subject_name: str

class SubjectResponse(BaseModel):
    subject_id: int
    subject_name: str
