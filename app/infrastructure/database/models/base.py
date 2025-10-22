"""
Base model con campos comunes
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base  # type: ignore[attr-defined]


class BaseModel(Base):  # type: ignore[misc]
    """
    Modelo base con campos comunes
    """

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
