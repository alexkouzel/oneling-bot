import time

from models import Reminder, Chat, Dictionary

DEFAULT_REMINDER_INTERVALS = [h * 60 for h in [5, 30, 120, 720, 2880]]

DEFAULT_DICTIONARY = Dictionary("nl", "en")


class Repository:
    def __init__(self):
        self.chats: dict[int, Chat] = {}

    # ----------------------------------------------------------------
    #  @reminders
    # ----------------------------------------------------------------

    def get_reminder(self, chat_id: int, reminder_id: int) -> Reminder:
        return self.get_chat(chat_id).reminders.get(reminder_id)

    def save_reminder(self, chat_id: int, reminder: Reminder) -> None:
        chat = self.get_chat(chat_id)

        # remove reminder with the same src and dst
        chat.reminders = {
            k: v
            for k, v in chat.reminders.items()
            if not (v.text == reminder.text and v.dictionary == reminder.dictionary)
        }

        chat.reminders[reminder.id] = reminder
        chat.reminder_next_id += 1

    def remove_reminder(self, chat_id: int, reminder_id: int) -> Reminder:
        chat = self.get_chat(chat_id)

        return chat.reminders.pop(reminder_id, None)

    def clear_reminders(self, chat_id: int) -> None:
        self.get_chat(chat_id).reminders.clear()

    def handle_reminder_call(self, chat_id: int, reminder_id: int) -> None:
        chat = self.get_chat(chat_id)

        reminder = chat.reminders[reminder_id]
        reminder.left -= 1

        if reminder.left == 0:
            chat.reminders.pop(reminder.id)
        else:
            reminder.last_at = time.time()

    # ----------------------------------------------------------------
    #  @chats
    # ----------------------------------------------------------------

    def get_chat(self, id: int) -> Chat:

        if id not in self.chats:
            return self.create_chat(id, DEFAULT_REMINDER_INTERVALS, DEFAULT_DICTIONARY)

        return self.chats[id]

    def get_all_chats(self) -> list[Chat]:
        return self.chats.values()

    def create_chat(
        self, id: int, reminder_intervals: list[int], dictionary: Dictionary
    ) -> Chat:
        chat = Chat(id, {}, reminder_intervals, 0, dictionary)
        self.chats[id] = chat

        return chat

    def update_reminder_intervals(
        self, chat_id: int, reminder_intervals: list[int]
    ) -> None:

        self.get_chat(chat_id).reminder_intervals = reminder_intervals

        # clear entries as they use old intervals
        self.clear_reminders(chat_id)

    def update_dictionary(self, chat_id: int, dictionary: Dictionary) -> None:
        self.get_chat(chat_id).dictionary = dictionary
