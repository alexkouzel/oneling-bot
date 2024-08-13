from dataclasses import dataclass


@dataclass
class Dictionary:
    src: str
    dst: str


@dataclass
class Reminder:
    id: int
    last_at: int
    left: int
    text: str
    translations: list[str]
    has_examples: bool
    dictionary: Dictionary


@dataclass
class Chat:
    id: int
    reminders: dict[int, Reminder]
    reminder_intervals: list[int]
    reminder_next_id: int
    dictionary: Dictionary

    def get_reminder_interval(self, reminder: Reminder) -> int:
        return self.reminder_intervals[-reminder.left]
