import logging
import time

from telegram import Update
from telegram.error import NetworkError
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from models import Chat, Entry
from repository import Repository
from utils import time_to_str, str_to_time


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARN
)

repository = Repository()

help_message = """

You can control me by sending these commands:

/add {value} - add a new reminder
/remove {value} - remove a reminder
/list - list all reminders
/clear - clear all reminders
/set_intervals {intervals} - set reminder intervals (also clears reminders)
/show_intervals - display current reminder intervals

The default intervals are '5m 30m 2h 12h 2d', which means a reminder will first occur after 5 min, then after 30 min, etc.

Also, for adding a new reminder you can just write the value in the chat without using /add.

"""


def get_chat(update: Update) -> Chat:
    return repository.get_chat(update.effective_chat.id)


def next_remind_msg(chat: Chat, entry: Entry) -> str:
    if entry.reminded_count < len(chat.intervals):
        next_remind = chat.intervals[entry.reminded_count]
        return f"\n\n** next reminder in {time_to_str(next_remind)} **"
    else:
        return "\n\n** last reminder **"


async def remind_entry(chat: Chat, entry: Entry, context: ContextTypes.DEFAULT_TYPE):
    repository.remind_entry(entry)

    message = entry.value + next_remind_msg(chat, entry)
    await context.bot.send_message(chat_id=chat.id, text=message)


async def reminder(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()

    for chat in repository.get_all_chats().values():
        for entry in list(chat.entries.values()):

            next_remind = chat.intervals[entry.reminded_count]
            time_passed = now - entry.last_reminded_at

            if time_passed > next_remind:
                await remind_entry(chat, entry, context)


async def add_entry(value: str, update: Update):
    chat = get_chat(update)

    if value in chat.entries:
        await update.message.reply_text("This reminder is already in your list")
        return

    entry = Entry(chat.id, time.time(), 0, value)
    repository.add_entry(chat, entry)

    message = f"'{value}' is added to your list{next_remind_msg(chat, entry)}"
    await update.message.reply_text(message)


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_entry(update.message.text, update)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(help_message)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_entry(" ".join(context.args), update)


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)
    value = " ".join(context.args)

    removed = repository.remove_entry(chat.id, value)
    message = "will no longer be reminded" if removed else "is not in your list"

    await update.message.reply_text(f"'{value}' {message}")


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)

    if not chat.entries:
        await update.message.reply_text("Your list is empty")
        return

    values = [f"{i+1}. {entry.value}" for i, entry in enumerate(chat.entries.values())]
    message = "\n".join(values)

    await update.message.reply_text(message)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repository.clear_entries(update.effective_chat.id)
    await update.message.reply_text("Your list is now empty")


async def set_intervals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intervals = [str_to_time(arg) for arg in context.args]

    if len(intervals) == 0 or any(time == -1 for time in intervals):
        await update.message.reply_text("Invalid reminder intervals. Try again")
        return

    chat_id = update.effective_chat.id
    repository.update_intervals(chat_id, intervals)
    repository.clear_entries(chat_id)

    await update.message.reply_text("Your reminder intervals are updated")


async def show_intervals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intervals = " ".join([time_to_str(time) for time in get_chat(update).intervals])
    await update.message.reply_text("Your reminder intervals: " + intervals)


def main(token: str):
    while True:
        try:
            app = ApplicationBuilder().token(token).build()

            app.job_queue.run_repeating(reminder, interval=1)

            app.add_handler(CommandHandler(["start", "help"], help_command))
            app.add_handler(CommandHandler("add", add_command))
            app.add_handler(CommandHandler("remove", remove_command))
            app.add_handler(CommandHandler("list", list_command))
            app.add_handler(CommandHandler("clear", clear_command))
            app.add_handler(CommandHandler("set_intervals", set_intervals_command))
            app.add_handler(CommandHandler("show_intervals", show_intervals_command))
            app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message))

            app.run_polling()

        except Exception:
            time.sleep(10)
