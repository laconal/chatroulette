from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from chatroullete.enums import CloseReason, RoomStatus
from chatroullete.models.base import Base, CreatedAtMixin, str_enum


class Room(CreatedAtMixin, Base):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("user1_id <> user2_id", name="distinct_members"),
        # A user can sit in at most one open room on each side; matchmaking
        # guarantees the rest by locking both user rows.
        Index(
            "uq_rooms_open_user1",
            "user1_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        Index(
            "uq_rooms_open_user2",
            "user2_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user1_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user2_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[RoomStatus] = mapped_column(
        str_enum(RoomStatus), default=RoomStatus.OPEN, server_default=RoomStatus.OPEN.value
    )
    close_reason: Mapped[CloseReason | None] = mapped_column(str_enum(CloseReason))
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def members(self) -> tuple[int, int]:
        return self.user1_id, self.user2_id
