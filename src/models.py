from dataclasses import dataclass


@dataclass
class Entry:
    idx: int
    chat_id: int
    last_reminded_at: int
    reminders_left: int
    src: str
    dst: str
    examples: list[str]


@dataclass
class Dictionary:
    src: str
    dst: str


@dataclass
class Chat:
    id: int
    next_idx: int
    entries: dict[str, Entry]
    intervals: list[int]
    dictionary: Dictionary

    def get_interval(self, entry: Entry):
        return self.intervals[-entry.reminders_left]
