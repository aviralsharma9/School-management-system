from pydantic import BaseModel

class SectionResponse(BaseModel):
    section_id: int
    class_name: str
    section_name: str

class SectionCreate(BaseModel):
    class_id: int
    section_name: str

class ClassCreate(BaseModel):
    class_name: str

class ClassResponse(BaseModel):
    class_id: int
    class_name: str