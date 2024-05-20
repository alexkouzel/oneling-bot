from dataclasses import dataclass


@dataclass
class Entry:
    idx: int
    chat_id: int
    last_reminded_at: int
    reminders_left: int
    value: str


@dataclass
class Chat:
    id: int
    next_idx: int
    entries: dict[str, Entry]
    intervals: list[int]
