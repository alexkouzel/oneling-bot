from dataclasses import dataclass


@dataclass
class Dictionary:
    src: str
    dst: str


@dataclass
class Example:
    src: str
    dst: str


@dataclass
class Destination:
    value: str
    examples: list[Example]


@dataclass
class Translation:
    src: str
    dst: list[Destination]
    definition: str

    def get_dst_values(self) -> list[str]:
        return [dst.value for dst in self.dst]

    def get_examples(self) -> list[Example]:
        return [example for dst in self.dst for example in dst.examples]


@dataclass
class Reminder:
    id: int
    last_at: int
    left: int
    translation: Translation
    dictionary: Dictionary


@dataclass
class Chat:
    id: int
    reminders: dict[int, Reminder]
    reminder_next_id: int
    reminder_intervals: list[int]
    dictionary: Dictionary

    def get_reminder_interval(self, reminder: Reminder) -> int:
        return self.reminder_intervals[-reminder.left]
