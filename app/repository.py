from models import Chat, Entry
import time


class Repository:
    def __init__(self):
        self.chats: dict[int, Chat] = {}

    def get_all_chats(self):
        return self.chats

    def remind_entry(self, entry: Entry):
        chat = self.chats[entry.chat_id]
        entry.reminders_left -= 1

        if entry.reminders_left == 0:
            chat.entries.pop(entry.idx)
        else:
            entry.last_reminded_at = time.time()

    def add_entry(self, chat: Chat, entry: Entry):
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

    def get_chat(self, id: int):
        if id not in self.chats:
            intervals = [h * 60 for h in [5, 30, 120, 720, 2880]]
            self.chats[id] = Chat(id, 0, {}, intervals)

        return self.chats[id]
