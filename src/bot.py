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

from models import Entry, Chat, Dictionary
from utils import time_to_text, text_to_time

from linguee.api import translations

# ----------------------------------------------------------------
#  Languages
# ----------------------------------------------------------------

LANGUAGES = {
    "bg": "Bulgarian",
    "cs": "Czech",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "fi": "Finnish",
    "fr": "French",
    "hu": "Hungarian",
    "it": "Italian",
    "ja": "Japanese",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "mt": "Maltese",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovene",
    "sv": "Swedish",
    "zh": "Chinese",
}

# ----------------------------------------------------------------
#  Repository
# ----------------------------------------------------------------
# The repository is used to store user chats & entries.

from repository import Repository

repository = Repository()

# ----------------------------------------------------------------
#  Logging
# ----------------------------------------------------------------

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARN,
)

# ----------------------------------------------------------------
#  Utils
# ----------------------------------------------------------------


def get_chat(update: Update) -> Chat:
    return repository.get_chat(update.effective_chat.id)


# ----------------------------------------------------------------
#  Help
# ----------------------------------------------------------------


def get_help_message(chat: Chat):
    return f"""

You can control me by sending these commands:

/list - list reminders
/clear - clear reminders
/set_intervals {{intervals}} - set intervals
/show_intervals - show intervals

Also, to add a new reminder, simply type the value in the chat.

Current intervals: {get_intervals_text(chat.intervals)}
Current dictionary: {get_dictionary_text(chat.dictionary)}

"""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)
    message = get_help_message(chat)

    await update.message.reply_text(message, parse_mode="HTML")


# ----------------------------------------------------------------
#  Dictionary
# ----------------------------------------------------------------


async def switch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)

    new_dictionary = Dictionary(chat.dictionary.dst, chat.dictionary.src)

    repository.update_dictionary(chat.id, new_dictionary)

    message = "Success! The new dictionary: " + get_dictionary_text(new_dictionary)
    await update.message.reply_text(message)


async def set_dictionary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: Implement this.
    return


async def choose_dictionary():
    # TODO: Implement this.
    return


def get_dictionary_text(dictionary: Dictionary):
    src = LANGUAGES[dictionary.src]
    dst = LANGUAGES[dictionary.dst]

    return f"{src} -> {dst}"


# ----------------------------------------------------------------
#  Reminder Intervals
# ----------------------------------------------------------------

set_intervals_usage = """

Usage: /set_intervals {intervals}

e.g. /set_intervals 5m 30m 2h 12h 2d

Time units: s (seconds), m (minutes), h (hours), d (days)

"""


async def set_intervals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intervals = [text_to_time(arg) for arg in context.args]

    if len(intervals) == 0:
        return await update.message.reply_text(set_intervals_usage)

    are_invalid = any(time == -1 for time in intervals)

    if are_invalid:
        await update.message.reply_text("Invalid intervals. Try again")
        await update.message.reply_text(set_intervals_usage)
        return

    chat_id = update.effective_chat.id

    # update intervals in the repository
    repository.update_intervals(chat_id, intervals)

    # clear entries as they use old intervals
    repository.clear_entries(chat_id)

    await update.message.reply_text(
        "Success! Intervals are updated and all previous entries were cleared"
    )


async def show_intervals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intervals = get_chat(update).intervals
    message = "Intervals: " + get_intervals_text(intervals)

    await update.message.reply_text(message)


def get_intervals_text(intervals: list[int]):
    result = [time_to_text(interval) for interval in intervals]
    result = " ".join(result)

    return result


# ----------------------------------------------------------------
#  Reminder Management (listing, cleaning, etc.)
# ----------------------------------------------------------------


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)

    if not chat.entries:
        return await update.message.reply_text("Your list is empty")

    entry_list = [f"{entry.src} - {entry.dst}" for entry in chat.entries.values()]
    entry_list = "\n".join(entry_list)

    await update.message.reply_text(entry_list)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    repository.clear_entries(chat_id)

    await update.message.reply_text("Your list is now empty")


# ----------------------------------------------------------------
#  Reminder Creation
# ----------------------------------------------------------------


async def create_entry(chat: Chat, value: str):
    lemmas = await translations(value, chat.dictionary.src, chat.dictionary.dst)

    if not lemmas:
        return None

    idx = chat.next_idx

    last_reminded_at = time.time()
    reminders_left = len(chat.intervals)

    src = get_entry_src(lemmas)
    dst = get_entry_dst(lemmas)
    examples = get_entry_examples(lemmas)

    return Entry(idx, chat.id, last_reminded_at, reminders_left, src, dst, examples)


async def create_reminder(
    value: str, update: Update, context: ContextTypes.DEFAULT_TYPE
):
    chat = get_chat(update)

    entry = await create_entry(chat, value)

    if not entry:
        return await update.message.reply_text("The value is not found. Try again")
    
    repository.add_entry(chat.id, entry)

    await send_reminder(chat, entry, context)


def get_entry_src(lemmas):
    return lemmas[0].text


def get_entry_dst(lemmas):
    translations = set()

    for lemma in lemmas:
        for translation in lemma.translations:
            translations.add(translation.text)

    translations = list(translations)[:3]

    return " / ".join(translations)


def get_entry_examples(lemmas):
    translation_examples = [
        example.dst
        for lemma in lemmas
        for translation in lemma.translations
        for example in translation.examples
    ]
    return translation_examples[:2]


# ----------------------------------------------------------------
#  Reminder Sending
# ----------------------------------------------------------------


async def send_reminder(chat: Chat, entry: Entry, context: ContextTypes.DEFAULT_TYPE):
    text = get_reminder_text(chat, entry)
    keyboard = get_reminder_keyboard(entry)

    await context.bot.send_message(
        chat_id=chat.id,
        text=text,
        reply_markup=keyboard,
    )


def get_reminder_text(chat: Chat, entry: Entry) -> str:
    examples = get_reminder_text_examples(entry)
    left = get_reminder_text_left(chat, entry)

    return f"{entry.src} - {entry.dst}\n{examples}\n{left}"


def get_reminder_text_examples(entry: Entry) -> str:
    if not entry.examples:
        return ""

    result = ["- " + example for example in entry.examples]
    result = "\n" + "\n".join(result) + "\n"

    return result


def get_reminder_text_left(chat: Chat, entry: Entry) -> str:
    if entry.reminders_left == 0:
        return "** last reminder **"

    next_reminder = time_to_text(chat.get_interval(entry))

    return "Next reminder in: {}\nReminders left: {}".format(
        next_reminder, entry.reminders_left
    )


def get_reminder_keyboard(entry: Entry) -> InlineKeyboardMarkup:
    if entry.reminders_left == 0:
        return None

    stop_btn = InlineKeyboardButton("Stop", callback_data=f"stop|{entry.idx}")

    return InlineKeyboardMarkup([[stop_btn]])


async def stop_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, args: list[str]
):
    chat_id = update.effective_chat.id
    entry_idx = int(args[1])

    is_reminder_removed = repository.remove_entry(chat_id, entry_idx)

    response = (
        "Reminder is stopped"
        if is_reminder_removed
        else "Reminder is no longer in your list"
    )

    await context.bot.send_message(chat_id=chat_id, text=response)


# ----------------------------------------------------------------
#  Reminder Caller
# ----------------------------------------------------------------


async def call_reminder(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()

    for chat in repository.get_all_chats().values():
        for entry in list(chat.entries.values()):

            time_to_remind = (now - entry.last_reminded_at) > chat.get_interval(entry)

            if time_to_remind:
                repository.handle_entry_reminder(entry)
                await send_reminder(chat, entry, context)


# ----------------------------------------------------------------
#  Common Bot Handlers
# ----------------------------------------------------------------


async def non_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text

    await create_reminder(value, update, context)


async def keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    args = query.data.split("|")

    match args[0]:
        case "stop":
            await stop_callback(update, context, args)
        case _:
            return


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        raise context.error
    except Conflict:
        # ignore conflicts as they occur during redeploys
        return


# ----------------------------------------------------------------
#  Bot Runner
# ----------------------------------------------------------------


def run(token: str):
    app = ApplicationBuilder().token(token).build()

    # run entry reminder every 1 second
    app.job_queue.run_repeating(call_reminder, interval=1)

    # handle errors during bot operation
    app.add_error_handler(error_handler)

    # handle callback from keyboards
    app.add_handler(CallbackQueryHandler(keyboard_handler))

    # handle bot commands
    app.add_handler(CommandHandler(["start", "help"], help_command))
    app.add_handler(CommandHandler("switch", switch_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("set_intervals", set_intervals_command))
    app.add_handler(CommandHandler("show_intervals", show_intervals_command))

    # handle non-command messages
    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), non_command_handler)
    )

    # run the bot using 'polling'
    app.run_polling()
