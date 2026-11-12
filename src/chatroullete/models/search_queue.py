from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from chatroullete.models.base import Base, CreatedAtMixin


class SearchQueue(CreatedAtMixin, Base):
    """Users currently waiting for a partner."""

    __tablename__ = "search_queue"
    __table_args__ = (Index("ix_search_queue_created_at", "created_at"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
