from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from uuid import uuid4


class Base(DeclarativeBase):
    pass


class BaseModel:
    id: Mapped[str] = mapped_column(
        SQLUUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )