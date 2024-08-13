from dataclasses import dataclass


@dataclass
class Dictionary:
    src: str
    dst: str


@dataclass
class Translation:
    text: str
    examples: list[tuple[str, str]]


@dataclass
class Lemma:
    pos: str
    translations: list[Translation]


@dataclass
class Reminder:
    id: int

    last_at: int
    left: int

    text: str
    lemmas: list[Lemma]

    dictionary: Dictionary

    def get_translations(self) -> list[str]:
        return [
            translation.text
            for lemma in self.lemmas
            for translation in lemma.translations
        ]

    def get_examples(self) -> list[tuple[str, str]]:
        return [
            example
            for lemma in self.lemmas
            for translation in lemma.translations
            for example in translation.examples
        ]

    def has_examples(self) -> bool:
        return any(self.get_examples())


@dataclass
class Chat:
    id: int

    reminders: dict[int, Reminder]
    reminder_intervals: list[int]
    reminder_next_id: int

    dictionary: Dictionary

    def get_reminder_interval(self, reminder: Reminder) -> int:
        return self.reminder_intervals[-reminder.left]
