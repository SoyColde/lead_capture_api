from sqlalchemy import Column, Integer, String
from codigo_fuente.database import Base
from datetime import datetime, timezone
from sqlalchemy import DateTime
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


