from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from chatroullete.models.base import Base, CreatedAtMixin


class Review(CreatedAtMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("room_id", "author_id"),
        CheckConstraint("score BETWEEN 1 AND 5", name="score_range"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    score: Mapped[int] = mapped_column(SmallInteger)
