import time

from models import Entry, Chat, Dictionary


class Repository:
    def __init__(self):
        self.chats: dict[int, Chat] = {}

    def get_all_chats(self):
        return self.chats

    def handle_entry_reminder(self, entry: Entry):
        chat = self.chats[entry.chat_id]
        entry.reminders_left -= 1

        if entry.reminders_left == 0:
            chat.entries.pop(entry.idx)
        else:
            entry.last_reminded_at = time.time()

    def add_entry(self, chat_id: int, entry: Entry):
        chat = self.chats[chat_id]

        # remove previous entry with the same src (if exists)
        chat.entries = {idx: e for idx, e in chat.entries.items() if e.src != entry.src}

        chat.entries[entry.idx] = entry
        chat.next_idx += 1

    def remove_entry(self, chat_id: int, idx: int):
        chat = self.chats[chat_id]

        if idx in chat.entries:
            chat.entries.pop(idx)
            return True

        return False

    def clear_entries(self, chat_id: int):
        self.chats[chat_id].entries.clear()

    def update_intervals(self, chat_id: int, intervals: list[int]):
        self.get_chat(chat_id).intervals = intervals

    def update_dictionary(self, chat_id: int, dictionary: Dictionary):
        self.get_chat(chat_id).dictionary = dictionary

    def get_chat(self, id: int):
        if id not in self.chats:

            default_intervals = [h * 60 for h in [5, 30, 120, 720, 2880]]
            default_dictionary = Dictionary("en", "nl")

            self.chats[id] = Chat(id, 0, {}, default_intervals, default_dictionary)

        return self.chats[id]
