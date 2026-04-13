import uuid
from sqlalchemy import Column, String, Text, Numeric, ARRAY, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from backend.database.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)
    agent_id = Column(String(50), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Property(Base):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(50), nullable=True)
    title = Column(String(255))
    location = Column(String(255))
    property_type = Column(String(50))
    amenities = Column(ARRAY(Text))
    actual_price = Column(Numeric)
    quoted_price = Column(Numeric)
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    title = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"))
    sender = Column(String(10), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    tool_used = Column(String(50), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    preferred_location = Column(String(255), nullable=True)
    budget = Column(Numeric, nullable=True)
    property_type = Column(String(50), nullable=True)
