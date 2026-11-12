from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from chatroullete.models.base import Base, CreatedAtMixin


class Message(CreatedAtMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_room_id_id", "room_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content_type: Mapped[str] = mapped_column(String(32))
    # Text or caption
    text: Mapped[str | None] = mapped_column(Text)
    file_id: Mapped[str | None] = mapped_column(String(256))
    # Message id in the sender's chat with the bot
    sender_message_id: Mapped[int] = mapped_column(BigInteger)
    # Id of the copy in the partner's chat, NULL if delivery failed
    delivered_message_id: Mapped[int | None] = mapped_column(BigInteger)
    # Full Telegram message, covers types without text or file (location, contact, ...)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB)
