from enum import StrEnum


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class Language(StrEnum):
    RU = "ru"
    EN = "en"
    UZ = "uz"
    UZ_CYRL = "uz_cyrl"


class RoomStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class CloseReason(StrEnum):
    LEFT = "left"
    IDLE = "idle"
    UNAVAILABLE = "unavailable"
