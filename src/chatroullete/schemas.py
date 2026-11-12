import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Self

from chatroullete.enums import CloseReason, Gender, Language, RoomStatus
from chatroullete.models import Room, User


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: int
    telegram_user_id: int
    ui_language: Language
    gender: Gender | None = None
    age: int | None = None
    chat_language: Language | None = None
    pref_gender: Gender | None = None
    pref_age_min: int | None = None
    pref_age_max: int | None = None

    @classmethod
    def from_model(cls, user: User) -> Self:
        return cls(
            id=user.id,
            telegram_user_id=user.telegram_user_id,
            ui_language=user.ui_language,
            gender=user.gender,
            age=user.age,
            chat_language=user.chat_language,
            pref_gender=user.pref_gender,
            pref_age_min=user.pref_age_min,
            pref_age_max=user.pref_age_max,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> Self:
        data = json.loads(raw)
        return cls(
            id=data["id"],
            telegram_user_id=data["telegram_user_id"],
            ui_language=Language(data["ui_language"]),
            gender=Gender(data["gender"]) if data["gender"] else None,
            age=data["age"],
            chat_language=Language(data["chat_language"]) if data["chat_language"] else None,
            pref_gender=Gender(data["pref_gender"]) if data["pref_gender"] else None,
            pref_age_min=data["pref_age_min"],
            pref_age_max=data["pref_age_max"],
        )


@dataclass(frozen=True, slots=True)
class RoomDTO:
    id: int
    user1_id: int
    user2_id: int
    status: RoomStatus
    created_at: datetime
    close_reason: CloseReason | None = None
    closed_by: int | None = None

    @classmethod
    def from_model(cls, room: Room) -> Self:
        return cls(
            id=room.id,
            user1_id=room.user1_id,
            user2_id=room.user2_id,
            status=room.status,
            created_at=room.created_at,
            close_reason=room.close_reason,
            closed_by=room.closed_by,
        )

    @property
    def members(self) -> tuple[int, int]:
        return self.user1_id, self.user2_id

    def partner_of(self, user_id: int) -> int:
        return self.user2_id if user_id == self.user1_id else self.user1_id


@dataclass(frozen=True, slots=True)
class Rating:
    average: float | None
    count: int
