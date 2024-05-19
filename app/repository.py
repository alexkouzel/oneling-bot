from models import Chat, Entry
import time


class Repository:
    def __init__(self):
        self.chats: dict[int, Chat] = {}

    def get_all_chats(self):
        return self.chats

    def remind_entry(self, entry: Entry):
        chat = self.chats[entry.chat_id]
        entry.reminded_count += 1
        
        if entry.reminded_count == len(chat.intervals):
            chat.entries.pop(entry.value) 
        else:
            entry.last_reminded_at = time.time()
        

    def add_entry(self, chat: Chat, entry: Entry):
        chat.entries[entry.value] = entry

    def remove_entry(self, chat_id: int, value: str):
        chat = self.chats[chat_id]
        
        if value in chat.entries:
            chat.entries.pop(value)
            return True

        return False

    def clear_entries(self, chat_id: int):
        self.chats[chat_id].entries.clear()

    def clear_old_entries(self):
        for chat in self.chats.values():
            for entry in chat.entries.values():
                if entry.reminded_count >= len(chat.intervals):
                    chat.entries.pop(entry.value)

    def update_intervals(self, chat_id: int, intervals: list[int]):
        self.get_chat(chat_id).intervals = intervals

    def get_chat(self, id: int):
        if id not in self.chats:
            intervals = [h * 60 for h in [5, 30, 120, 720, 2880]]
            self.chats[id] = Chat(id, {}, intervals)

        return self.chats[id]
