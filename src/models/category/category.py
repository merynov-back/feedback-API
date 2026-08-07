from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import mapped_column, Mapped

from src.models.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
