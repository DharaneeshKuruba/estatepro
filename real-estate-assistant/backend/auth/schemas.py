import uuid
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "buyer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = None   # Role selected on the frontend; validated server-side


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    agent_id: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AgentCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    agent_id: str
