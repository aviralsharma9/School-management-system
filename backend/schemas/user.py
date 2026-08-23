from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    name: str
    password: str

class UserResponse(BaseModel):
    username: str
    name: str
    is_active: bool
    roles: list[str]

class RoleAssignment(BaseModel):
    role: str