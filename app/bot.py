import logging
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Conflict
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    CallbackQueryHandler,
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

/list - list reminders
/clear - clear reminders
/set_intervals {intervals} - set reminder intervals
/show_intervals - show reminder intervals

<b>Default Intervals</b>
The default intervals are '5m 30m 2h 12h 2d', meaning a reminder will trigger first after 5 minutes, then after 30 minutes, and so on.

<b>Quick Tip</b>
To add a new reminder, simply type the value in the chat.

"""

set_intervals_usage = """

Usage: /set_intervals {intervals}

e.g. /set_intervals 5m 30m 2h 12h 2d

Time units: s (seconds), m (minutes), h (hours), d (days)

"""


def get_chat(update: Update) -> Chat:
    return repository.get_chat(update.effective_chat.id)


def get_interval(chat: Chat, entry: Entry) -> int:
    return chat.intervals[-entry.reminders_left]


def entry_info(chat: Chat, entry: Entry) -> str:
    if entry.reminders_left == 0:
        return "** last reminder **"

    next_reminder = time_to_str(get_interval(chat, entry))
    return f"Next reminder in: {next_reminder}\nReminders left: {entry.reminders_left}"


# ----------------------------------------------------------------
#  Inline Keyboards
# ----------------------------------------------------------------


def entry_keyboard(entry: Entry) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Stop", callback_data=f"stop|{entry.idx}")]]
    )


# ----------------------------------------------------------------
#  Entry Reminder
# ----------------------------------------------------------------


async def remind_entry(chat: Chat, entry: Entry, context: ContextTypes.DEFAULT_TYPE):
    repository.remind_entry(entry)

    text = f"{entry.value}\n\n{entry_info(chat, entry)}"
    keyboard = None if entry.reminders_left == 0 else entry_keyboard(entry)

    await context.bot.send_message(chat_id=chat.id, text=text, reply_markup=keyboard)


async def reminder(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()

    for chat in repository.get_all_chats().values():
        for entry in list(chat.entries.values()):
            if (now - entry.last_reminded_at) > get_interval(chat, entry):
                await remind_entry(chat, entry, context)


# ----------------------------------------------------------------
#  Callback Queries
# ----------------------------------------------------------------


async def stop_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, args: list[str]
):
    chat_id = update.effective_chat.id
    entry_idx = int(args[1])

    text = (
        "Reminder is stopped"
        if repository.remove_entry(chat_id, entry_idx)
        else "Reminder is no longer in your list"
    )
    await context.bot.send_message(chat_id=chat_id, text=text)


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    args = query.data.split("|")
    match args[0]:
        case "stop":
            await stop_callback(update, context, args)
        case _:
            return


# ----------------------------------------------------------------
#  Non-Command Messages
# ----------------------------------------------------------------


async def non_command_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text
    chat = get_chat(update)

    entry = Entry(chat.next_idx, chat.id, time.time(), len(chat.intervals), value)
    repository.add_entry(chat, entry)

    text = f"{value}\n\n{entry_info(chat, entry)}"
    await update.message.reply_text(text, reply_markup=entry_keyboard(entry))


# ----------------------------------------------------------------
#  Commands
# ----------------------------------------------------------------


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(help_message, parse_mode="HTML")


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)

    if not chat.entries:
        await update.message.reply_text("Your list is empty")
        return

    values = [f"({entry.idx}) {entry.value}" for entry in chat.entries.values()]
    message = "\n".join(values)

    await update.message.reply_text(message)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repository.clear_entries(update.effective_chat.id)
    await update.message.reply_text("Your list is now empty")


async def set_intervals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intervals = [str_to_time(arg) for arg in context.args]

    if len(intervals) == 0:
        await update.message.reply_text(set_intervals_usage)
        return

    if any(time == -1 for time in intervals):
        await update.message.reply_text("Invalid intervals. Try again")
        await update.message.reply_text(set_intervals_usage)
        return

    chat_id = update.effective_chat.id
    repository.update_intervals(chat_id, intervals)

    # clear entries as they use old intervals
    repository.clear_entries(chat_id)

    await update.message.reply_text("Success! Intervals are updated")


async def show_intervals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intervals = [time_to_str(time) for time in get_chat(update).intervals]
    intervals = " ".join(intervals)

    await update.message.reply_text("Your intervals: " + intervals)


# ----------------------------------------------------------------
#  Error Handler
# ----------------------------------------------------------------


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        raise context.error
    except Conflict:
        # ignore conflicts as they occur during redeploys
        return


# ----------------------------------------------------------------
#  Application Runner
# ----------------------------------------------------------------


def main(token: str):
    app = ApplicationBuilder().token(token).build()

    app.job_queue.run_repeating(reminder, interval=1)

    app.add_error_handler(error_handler)
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(CommandHandler(["start", "help"], help_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("set_intervals", set_intervals_command))
    app.add_handler(CommandHandler("show_intervals", show_intervals_command))
    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), non_command_message)
    )

    app.run_polling()
