import time
import threading

from models import Chat, Reminder, Dictionary

DEFAULT_REMINDER_INTERVALS = [h * 60 for h in [5, 30, 120, 720, 2880]]

DEFAULT_DICTIONARY = Dictionary("nl", "en")


class Repository:
    def __init__(self):
        self.chats: dict[int, Chat] = {}
        self.lock = threading.Lock()

    # ----------------------------------------------------------------
    #  @reminders
    # ----------------------------------------------------------------

    def get_active_reminders(self, chat_id: int) -> list[Reminder]:
        with self.lock:
            chat = self.get_chat(chat_id)
            
            reminders = chat.reminders.values()
            reminders = [reminder for reminder in reminders if reminder.left > 0]
            
            return reminders

    def get_reminder(self, chat_id: int, reminder_id: int) -> Reminder:
        with self.lock:
            chat = self.get_chat(chat_id)
            reminder = chat.reminders.get(reminder_id)
            
            return reminder

    def get_reminder(self, chat_id: int, src: str, dictionary: Dictionary) -> Reminder:
        with self.lock:
            chat = self.get_chat(chat_id)

            for reminder in chat.reminders.values():
                if (
                    reminder.translation.src == src
                    and reminder.dictionary == dictionary
                ):
                    return reminder
            
            return None

    def update_reminder(self, chat_id: int, reminder: Reminder) -> None:
        with self.lock:
            chat = self.get_chat(chat_id)
            chat.reminders[reminder.id] = reminder

    def save_reminder(self, chat_id: int, reminder: Reminder) -> None:
        with self.lock:
            chat = self.get_chat(chat_id)
            chat.reminders[reminder.id] = reminder
            chat.reminder_next_id += 1

    def remove_reminder(self, chat_id: int, reminder_id: int) -> Reminder:
        with self.lock:
            chat = self.get_chat(chat_id)

            reminder = chat.reminders[reminder_id]
            reminder.left = 0

            return reminder

    def clear_reminders(self, chat_id: int) -> None:
        with self.lock:
            chat = self.get_chat(chat_id)
            chat.reminders.clear()

    def handle_reminder_call(self, chat_id: int, reminder_id: int) -> None:
        with self.lock:
            chat = self.get_chat(chat_id)

            reminder = chat.reminders[reminder_id]
            reminder.last_at = time.time()
            reminder.left -= 1

    # ----------------------------------------------------------------
    #  @chats
    # ----------------------------------------------------------------

    def get_chat(self, id: int) -> Chat:
        with self.lock:

            if id not in self.chats:
                return self.create_chat(
                    id, DEFAULT_REMINDER_INTERVALS, DEFAULT_DICTIONARY
                )

            return self.chats[id]

    def get_all_chats(self) -> list[Chat]:
        with self.lock:
            return self.chats.values()

    def create_chat(
        self, id: int, reminder_intervals: list[int], dictionary: Dictionary
    ) -> Chat:
        with self.lock:

            reminders = {}
            reminder_next_id = 0

            chat = Chat(id, reminders, reminder_intervals, reminder_next_id, dictionary)
            self.chats[id] = chat

            return chat

    def update_reminder_intervals(
        self, chat_id: int, reminder_intervals: list[int]
    ) -> None:
        with self.lock:
            self.get_chat(chat_id).reminder_intervals = reminder_intervals

            # Clear entries as they use old intervals
            self.clear_reminders(chat_id)

    def update_dictionary(self, chat_id: int, dictionary: Dictionary) -> None:
        with self.lock:
            self.get_chat(chat_id).dictionary = dictionary
