"""
Database initialization: creates tables, sets up the role-limit trigger, and seeds initial data.
"""
import uuid
from decimal import Decimal
import re
from sqlalchemy import text
from backend.database.session import engine, SessionLocal
from backend.database.models import Base, User, Property
from backend.core.security import hash_password
from backend.rag.document_generator import PROPERTY_DOCS


ROLE_LIMIT_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION enforce_role_limits()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.role = 'admin' THEN
        IF (SELECT COUNT(*) FROM users WHERE role = 'admin') >= 1 THEN
            RAISE EXCEPTION 'Only one admin is allowed.';
        END IF;
    END IF;
    IF NEW.role = 'agent' THEN
        IF (SELECT COUNT(*) FROM users WHERE role = 'agent') >= 3 THEN
            RAISE EXCEPTION 'Maximum of three agents allowed.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS role_limit_trigger ON users;

CREATE TRIGGER role_limit_trigger
BEFORE INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION enforce_role_limits();
"""

SEED_USERS = [
    {
        "id": str(uuid.uuid4()),
        "name": "System Admin",
        "email": "admin@realestate.com",
        "password": "Admin@123",
        "role": "admin",
        "agent_id": None,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Agent One",
        "email": "agent1@realestate.com",
        "password": "Agent@123",
        "role": "agent",
        "agent_id": "AG001",
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Agent Two",
        "email": "agent2@realestate.com",
        "password": "Agent@123",
        "role": "agent",
        "agent_id": "AG002",
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Agent Three",
        "email": "agent3@realestate.com",
        "password": "Agent@123",
        "role": "agent",
        "agent_id": "AG003",
    },
]


def init_db():
    """Create tables and install trigger."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text(ROLE_LIMIT_TRIGGER_SQL))
        conn.commit()
    print("[DB] Tables created and role-limit trigger installed.")


def seed_db():
    """Insert admin/agents and seed properties if missing."""
    db = SessionLocal()
    try:
        for user_data in SEED_USERS:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing:
                user = User(
                    id=uuid.UUID(user_data["id"]),
                    name=user_data["name"],
                    email=user_data["email"],
                    password_hash=hash_password(user_data["password"]),
                    role=user_data["role"],
                    agent_id=user_data["agent_id"],
                )
                db.add(user)

        # Seed properties from synthetic source data
        def _parse_money(value: str) -> Decimal:
            normalized = re.sub(r"[^\d.]", "", value or "")
            return Decimal(normalized) if normalized else Decimal("0")

        for agent_id, props in PROPERTY_DOCS.items():
            for p in props:
                exists = db.query(Property).filter(
                    Property.agent_id == agent_id,
                    Property.title == p["title"],
                    Property.location == p["location"],
                ).first()
                if exists:
                    continue

                prop = Property(
                    id=uuid.uuid5(uuid.NAMESPACE_DNS, p["property_id"]),
                    agent_id=agent_id,
                    title=p["title"],
                    location=p["location"],
                    property_type=p["property_type"],
                    amenities=[a.strip() for a in p["amenities"].split(",") if a.strip()],
                    actual_price=_parse_money(p["actual_price"]),
                    quoted_price=_parse_money(p["quoted_price"]),
                    description=p["description"],
                )
                db.add(prop)

        db.commit()
        print("[DB] Seed data inserted successfully.")
    except Exception as e:
        db.rollback()
        print(f"[DB] Seeding error (may already exist): {e}")
    finally:
        db.close()
