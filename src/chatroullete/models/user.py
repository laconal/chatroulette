from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from chatroullete.enums import Gender, Language
from chatroullete.models.base import Base, CreatedAtMixin, str_enum


class User(CreatedAtMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # Also the id of the user's private chat with the bot
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(256))

    gender: Mapped[Gender | None] = mapped_column(str_enum(Gender))
    age: Mapped[int | None] = mapped_column(SmallInteger)
    # NULL means "any language"
    chat_language: Mapped[Language | None] = mapped_column(str_enum(Language))
    ui_language: Mapped[Language] = mapped_column(str_enum(Language))

    # Partner preferences, NULL means "any"
    pref_gender: Mapped[Gender | None] = mapped_column(str_enum(Gender))
    pref_age_min: Mapped[int | None] = mapped_column(SmallInteger)
    pref_age_max: Mapped[int | None] = mapped_column(SmallInteger)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
