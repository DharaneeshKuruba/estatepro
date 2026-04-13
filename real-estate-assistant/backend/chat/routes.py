"""
Chat routes: send a message (with tool invocation) and manage sessions.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.database.models import ChatSession, Message, User
from backend.chat.schemas import ChatRequest, SessionCreate, SessionOut, MessageOut
from backend.auth.dependencies import get_current_user
from backend.rag.tools import run_tool

router = APIRouter(prefix="/chat", tags=["Chat"])

TOOL_NAMES = [
    "property_retrieval",
    "summarization",
    "market_analysis",
    "comparison",
    "investment_recommendation",
]


@router.post("/", response_model=dict)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message with a selected tool and get an AI response."""
    if payload.tool not in TOOL_NAMES:
        raise HTTPException(status_code=400, detail=f"Invalid tool. Choose from: {TOOL_NAMES}")

    # Create or validate session
    if payload.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == uuid.UUID(payload.session_id),
            ChatSession.user_id == current_user.id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
    else:
        session = ChatSession(
            id=uuid.uuid4(),
            user_id=current_user.id,
            title=payload.message[:60] + ("..." if len(payload.message) > 60 else ""),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # Store user message
    user_msg = Message(
        id=uuid.uuid4(),
        session_id=session.id,
        sender="user",
        content=payload.message,
        tool_used=payload.tool,
    )
    db.add(user_msg)
    db.commit()

    # Run the selected tool
    response_text = run_tool(
        tool=payload.tool,
        query=payload.message,
        user_role=current_user.role,
        agent_id=current_user.agent_id,
    )

    # Store assistant response
    ai_msg = Message(
        id=uuid.uuid4(),
        session_id=session.id,
        sender="assistant",
        content=response_text,
        tool_used=payload.tool,
    )
    db.add(ai_msg)
    db.commit()

    return {
        "session_id": str(session.id),
        "message": response_text,
        "tool_used": payload.tool,
    }


@router.post("/sessions", response_model=SessionOut)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ChatSession(
        id=uuid.uuid4(),
        user_id=current_user.id,
        title=payload.title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionOut(
        id=str(session.id),
        title=session.title,
        created_at=session.created_at.isoformat() if session.created_at else "",
    )


@router.get("/sessions/{user_id}", response_model=list[SessionOut])
def get_sessions(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all chat sessions for the current user."""
    if str(current_user.id) != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")
    sessions = db.query(ChatSession).filter(ChatSession.user_id == uuid.UUID(user_id)).order_by(ChatSession.created_at.desc()).all()
    return [
        SessionOut(id=str(s.id), title=s.title, created_at=s.created_at.isoformat() if s.created_at else "")
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
def get_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all messages in a session."""
    session = db.query(ChatSession).filter(
        ChatSession.id == uuid.UUID(session_id),
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    messages = db.query(Message).filter(Message.session_id == uuid.UUID(session_id)).order_by(Message.created_at).all()
    return [
        MessageOut(
            id=str(m.id),
            sender=m.sender,
            content=m.content,
            tool_used=m.tool_used,
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in messages
    ]
