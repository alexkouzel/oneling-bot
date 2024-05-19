from dataclasses import dataclass


@dataclass
class Entry:
    chat_id: int
    last_reminded_at: int
    reminded_count: int
    value: str


@dataclass
class Chat:
    id: int
    entries: dict[str, Entry]
    intervals: list[int]
