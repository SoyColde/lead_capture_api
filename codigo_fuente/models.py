from sqlalchemy import Column, Integer, String, ForeignKey, Index, Text
from codigo_fuente.database import Base
from datetime import datetime, timezone
from sqlalchemy import DateTime, JSON, CheckConstraint
from sqlalchemy.orm import mapped_column, relationship
from uuid import uuid4

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

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Identificador de usuario de la conversacion
    # / Pendiente de autenticacion individual

    created_at=Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    __table_args__ = (
        Index(
            "ix_conversation_messages_history",
            "conversation_id",
            "created_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True)

    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )