import uuid
from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    tool: str = "property_retrieval"


class SessionCreate(BaseModel):
    title: Optional[str] = "New Chat"


class MessageOut(BaseModel):
    id: str
    sender: str
    content: str
    tool_used: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: str
    title: Optional[str]
    created_at: str

    class Config:
        from_attributes = True
