import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.database.models import User
from backend.core.security import hash_password, verify_password, create_access_token
from backend.auth.schemas import UserRegister, UserLogin, TokenResponse, AgentCreate, UserOut
from backend.auth.dependencies import require_admin

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Public registration — only buyers allowed."""
    if payload.role != "buyer":
        raise HTTPException(
            status_code=403,
            detail="Only buyers can register. Admin and Agent accounts are system-controlled.",
        )
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = User(
        id=uuid.uuid4(),
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="buyer",
        agent_id=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email, "role": user.role, "agent_id": user.agent_id})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Login for all roles. Validates the claimed role if provided."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # ── Role validation ─────────────────────────────────────────────────────
    # If the frontend sent a role, verify it matches the user's actual role.
    if payload.role and payload.role != user.role:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Role mismatch: you selected '{payload.role}' but your account role is "
                f"'{user.role}'. Please select the correct role and try again."
            ),
        )

    token = create_access_token({"sub": user.email, "role": user.role, "agent_id": user.agent_id})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/logout")
def logout():
    """Client-side token invalidation."""
    return {"message": "Logged out successfully. Please clear your token on the client side."}


@router.post("/admin/create-agent", response_model=UserOut)
def create_agent(
    payload: AgentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin-only: create a new agent (max 3)."""
    agent_count = db.query(User).filter(User.role == "agent").count()
    if agent_count >= 3:
        raise HTTPException(status_code=400, detail="Maximum of three agents allowed.")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    agent = User(
        id=uuid.uuid4(),
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="agent",
        agent_id=payload.agent_id,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return UserOut.model_validate(agent)
