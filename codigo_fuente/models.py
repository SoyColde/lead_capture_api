from sqlalchemy import Column, Integer, String
from codigo_fuente.database import Base
from datetime import datetime, timezone
from sqlalchemy import DateTime, JSON, CheckConstraint
from sqlalchemy.orm import mapped_column

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True)
    phone = Column(String, unique=True)
    request = Column(String)
    notes = Column(String)
    temperature = Column(String, nullable=True)
    created_at = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class PendingAction(Base):
    __tablename__="pending_actions"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved', 'rejected', 'executed')",
            name="ck_pending_actions_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    tool_name = Column(String, nullable=False)
    arguments = Column(JSON, nullable=False)

    status = Column(
        String,
        nullable=False,
        default="pending",
    )

    requested_by = Column(String, nullable = True)
    approved_by = Column(String, nullable = True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda:datetime.now(timezone.utc),
        nullable=False,
    )

    decided_at = Column(DateTime(timezone=True), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)