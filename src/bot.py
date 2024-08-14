import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Conflict, NetworkError, InvalidToken
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from models import Reminder, Chat, Dictionary
from dictionary import get_examples, get_translations, get_query_overview
from utils import time_to_str, str_to_time

type CallbackArgs = tuple[Update, ContextTypes.DEFAULT_TYPE, list[str]]

type Example = tuple[str, str]

# ----------------------------------------------------------------
#  @constants
# ----------------------------------------------------------------

DEVELOPER_CHAT_ID = 597554184

DEFAULT_REMINDER_INTERVALS = [h * 60 for h in [5, 30, 120, 720, 2880]]

TRANSLATIONS_PER_REMINDER = 5
EXAMPLES_PER_REMINDER = 5

PRIMARY_LANGUAGE = "en"

LANGUAGES = {
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "ja": "Japanese",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
}

# ----------------------------------------------------------------
#  @repository
# ----------------------------------------------------------------
# The repository is used to store user chats & entries.

from repository import Repository

repository = Repository()

# ----------------------------------------------------------------
#  @logging
# ----------------------------------------------------------------

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARN,
)

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
#  @utils
# ----------------------------------------------------------------


def get_chat(update: Update) -> Chat:
    return repository.get_chat(update.effective_chat.id)


def to_2d(values: list) -> list[list]:
    return [values[i : i + 2] for i in range(0, len(values), 2)]


# ----------------------------------------------------------------
#  @default
# ----------------------------------------------------------------


async def chat_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Chat ID: {chat_id}")


def get_help_message(chat: Chat):
    return f"""

I can help you learn and remember words in different languages. By setting up reminders, it makes it easy to keep new vocabulary in mind.

<b>🔔 To manage reminders:</b>
/show_reminders - show all reminders
/clear_reminders - clear all reminders

To set a new reminder, simply type the word you want to remember directly in the chat.

<b>⏰ To manage intervals:</b>
/show_intervals - show current intervals
/set_intervals - set new intervals
/reset_intervals - reset intervals to default values

Note: Changing intervals will automatically clear all existing reminders, as they rely on the previous intervals.

<b>🌐 To manage dictionary:</b>
/show_dictionary - show current dictionary
/choose_dictionary - choose new dictionary
/switch_dictionary - switch source and destination languages

<b>⚙️ Current settings:</b>
Intervals: {str_intervals(chat.reminder_intervals)}
Dictionary: {str_dictionary(chat.dictionary)}

"""


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)

    await update.message.reply_text(get_help_message(chat), parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)

    await update.message.reply_text(get_help_message(chat), parse_mode="HTML")


# ----------------------------------------------------------------
#  @dictionary
# ----------------------------------------------------------------


async def switch_dictionary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)

    dictionary = Dictionary(chat.dictionary.dst, chat.dictionary.src)

    repository.update_dictionary(chat.id, dictionary)

    await update.message.reply_text(
        f'Dictionary is set to "{str_dictionary(dictionary)}"'
    )


async def show_dictionary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)

    await update.message.reply_text(str_dictionary(chat.dictionary))


async def choose_dictionary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dictionaries = [
        Dictionary(language, PRIMARY_LANGUAGE)
        for language in LANGUAGES
        if language != PRIMARY_LANGUAGE
    ]

    buttons = [
        InlineKeyboardButton(
            f"{str_dictionary(dictionary)}",
            callback_data=f"dictionary|{dictionary.src}|{dictionary.dst}",
        )
        for dictionary in dictionaries
    ]

    keyboard = InlineKeyboardMarkup(to_2d(buttons))

    await update.message.reply_text(
        "Please choose a dictionary. You can switch languages with /switch_dictionary",
        reply_markup=keyboard,
    )


async def dictionary_callback(args: CallbackArgs):
    (update, context, data) = args

    chat_id = update.effective_chat.id

    src = data[1]
    dst = data[2]

    dictionary = Dictionary(src, dst)

    repository.update_dictionary(chat_id, dictionary)

    await context.bot.send_message(
        chat_id, f'Dictionary is set to "{str_dictionary(dictionary)}"'
    )


def str_dictionary(dictionary: Dictionary) -> str:
    src = LANGUAGES[dictionary.src]
    dst = LANGUAGES[dictionary.dst]

    return f"{src} → {dst}"


# ----------------------------------------------------------------
#  @intervals
# ----------------------------------------------------------------

set_intervals_usage = """

Usage: /set_intervals {intervals}

e.g. /set_intervals 5m 30m 2h 12h 2d

Time units: s (seconds), m (minutes), h (hours), d (days)

"""


async def show_intervals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intervals = get_chat(update).reminder_intervals
    message = "Current intervals: " + str_intervals(intervals)

    await update.message.reply_text(message)


async def set_intervals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intervals = [str_to_time(arg) for arg in context.args]

    if len(intervals) == 0:
        await update.message.reply_text(set_intervals_usage)
        return

    are_invalid = any(time == -1 for time in intervals)

    if are_invalid:
        await update.message.reply_text("Invalid intervals. Try again")
        await update.message.reply_text(set_intervals_usage)
        return

    chat_id = update.effective_chat.id

    repository.update_reminder_intervals(chat_id, intervals)

    await update.message.reply_text(
        "Success! Intervals are updated to: " + str_intervals(intervals)
    )


async def reset_intervals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    repository.update_reminder_intervals(chat_id, DEFAULT_REMINDER_INTERVALS)

    await update.message.reply_text(
        "Intervals are reset to default values: 5m 30m 2h 12h 2d"
    )


def str_intervals(intervals: list[int]):
    result = [time_to_str(interval) for interval in intervals]
    result = " ".join(result)

    return result


# ----------------------------------------------------------------
#  @reminder_management
# ----------------------------------------------------------------


async def show_reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)

    if not chat.reminders:
        await update.message.reply_text("You have no reminders")
        return

    reminders = [
        f'{idx + 1}. <b>"{reminder.text}"</b> - {str_reminder_translations(reminder, TRANSLATIONS_PER_REMINDER)}'
        for idx, reminder in enumerate(chat.reminders.values())
    ]
    reminders = "\n".join(reminders)

    await update.message.reply_text(reminders, parse_mode="HTML")


def str_reminder_translations(reminder: Reminder, limit: int | None = None) -> str:
    translations = reminder.translations

    if limit != None and len(translations) > limit:
        return " / ".join(translations[:limit]) + " / ..."
    else:
        return " / ".join(translations)


async def clear_reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    repository.clear_reminders(chat_id)

    await update.message.reply_text("You no longer have any reminders")


# ----------------------------------------------------------------
#  @reminder_creation
# ----------------------------------------------------------------


async def create_reminder_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str
):
    chat = get_chat(update)

    reminder = await create_reminder(update, chat, value)

    if not reminder:
        return

    repository.save_reminder(chat.id, reminder)

    await send_reminder(context, chat, reminder)


async def create_reminder(update: Update, chat: Chat, value: str):
    result = await get_query_overview(value, chat.dictionary.src, chat.dictionary.dst)

    if not result:
        await update.message.reply_text(f'The value "{value}" is not found. Try again')
        return None

    id = chat.reminder_next_id

    last_at = time.time()
    left = len(chat.reminder_intervals)

    (text, translations, examples) = result

    return Reminder(
        id, last_at, left, text, translations, any(examples), chat.dictionary
    )


# ----------------------------------------------------------------
#  @reminder_sending
# ----------------------------------------------------------------


async def send_reminder(
    context: ContextTypes.DEFAULT_TYPE, chat: Chat, reminder: Reminder
):
    text = str_reminder(chat, reminder)
    keyboard = reminder_keyboard(reminder)

    await context.bot.send_message(
        chat_id=chat.id, text=text, reply_markup=keyboard, parse_mode="HTML"
    )


def str_reminder(chat: Chat, reminder: Reminder) -> str:
    left = str_reminder_left(chat, reminder)
    translations = str_reminder_translations(reminder, TRANSLATIONS_PER_REMINDER)

    return f'<b>"{reminder.text}"</b> - {translations}\n\n{left}'


def str_reminder_left(chat: Chat, reminder: Reminder) -> str:
    if reminder.left == 0:
        return "** last reminder **"

    next_reminder = time_to_str(chat.get_reminder_interval(reminder))

    return "Next reminder in: {}\nReminders left: {}/{}".format(
        next_reminder, reminder.left, len(chat.reminder_intervals)
    )


def reminder_keyboard(reminder: Reminder) -> InlineKeyboardMarkup:
    buttons = []

    # translations button
    if len(reminder.translations) > TRANSLATIONS_PER_REMINDER:
        data = f"translations|{reminder.text}|{reminder.dictionary.src}|{reminder.dictionary.dst}"
        btn = InlineKeyboardButton("All Translations", callback_data=data)
        buttons.append(btn)

    # examples button
    if reminder.has_examples:
        data = f"examples|{reminder.text}|{reminder.dictionary.src}|{reminder.dictionary.dst}"
        btn = InlineKeyboardButton("Examples", callback_data=data)
        buttons.append(btn)

    # stop button
    if reminder.left > 0:
        data = f"stop|{reminder.id}"
        btn = InlineKeyboardButton("Stop Reminder", callback_data=data)
        buttons.append(btn)

    return InlineKeyboardMarkup(to_2d(buttons))


async def stop_callback(args: CallbackArgs):
    await reminder_by_id_callback(
        args,
        repository.remove_reminder,
        lambda reminder: f'Reminder "{reminder.text}" is stopped',
    )


async def translations_callback(args: CallbackArgs):
    await reminder_by_text_callback(args, get_translations_str)


async def get_translations_str(text: str, src: str, dst: str) -> str:
    translations = await get_translations(text, src, dst)

    if not translations:
        return "Something went wrong. Try again later"

    return str_translations(translations)


def str_translations(translations: list[str]) -> str:
    return " / ".join(translations)


async def examples_callback(args: CallbackArgs):
    await reminder_by_text_callback(args, get_examples_str)


async def get_examples_str(text: str, src: str, dst: str) -> str:
    examples = await get_examples(text, src, dst)

    if not examples:
        return "Something went wrong. Try again later"

    return str_examples(await get_examples(text, src, dst))


def str_examples(examples: list[Example]) -> str:
    result = [
        f"<b>{idx + 1}. {src}</b>\nTranslation: {dst}\n"
        for idx, (src, dst) in enumerate(examples[:EXAMPLES_PER_REMINDER])
    ]
    result = "\n".join(result)
    return result


async def reminder_by_id_callback(
    args: CallbackArgs,
    reminder_action: callable,
    reminder_message: callable,
):
    (update, context, data) = args

    chat_id = update.effective_chat.id

    reminder_id = int(data[1])
    reminder = reminder_action(chat_id, reminder_id)

    if not reminder:
        await context.bot.send_message(chat_id, "Reminder is not found")
        return

    message = reminder_message(reminder)

    await context.bot.send_message(chat_id, message, parse_mode="HTML")


async def reminder_by_text_callback(args: CallbackArgs, action: callable):
    (update, context, data) = args

    chat_id = update.effective_chat.id
    message = await action(data[1], data[2], data[3])

    await context.bot.send_message(chat_id, message, parse_mode="HTML")


# ----------------------------------------------------------------
#  @reminder_caller
# ----------------------------------------------------------------


async def call_reminder(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()

    for chat in repository.get_all_chats():
        for reminder in chat.reminders.values():

            interval = chat.get_reminder_interval(reminder)
            time_to_remind = (now - reminder.last_at) > interval

            if time_to_remind:
                repository.handle_reminder_call(chat.id, reminder.id)
                await send_reminder(context, chat, reminder)


# ----------------------------------------------------------------
#  @common_handlers
# ----------------------------------------------------------------


async def non_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text

    await create_reminder_command(update, context, value)


async def keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    data = query.data.split("|")

    args = (update, context, data)

    match data[0]:
        case "stop":
            await stop_callback(args)
        case "dictionary":
            await dictionary_callback(args)
        case "examples":
            await examples_callback(args)
        case "translations":
            await translations_callback(args)
        case _:
            return


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("An error occurred: ", exc_info=context.error)

    # notify the developer about the error
    await context.bot.send_message(
        DEVELOPER_CHAT_ID, f"[LOG] An error occurred: {context.error}"
    )


async def invalid_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Invalid command. Type /help for more information")


# ----------------------------------------------------------------
#  @runner
# ----------------------------------------------------------------


def run_polling(token: str):
    app = ApplicationBuilder().token(token).build()

    # call reminders every 1 second
    app.job_queue.run_repeating(call_reminder, interval=1)

    # handle errors during bot operation
    app.add_error_handler(error_handler)

    # handle callback from keyboards
    app.add_handler(CallbackQueryHandler(keyboard_handler))

    # handle non-command messages
    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), non_command_handler)
    )

    # ----------------------------------------------------------------

    # handle default commands
    app.add_handler(CommandHandler("chat_id", chat_id_command))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    # handle reminder commands
    app.add_handler(CommandHandler("show_reminders", show_reminders_command))
    app.add_handler(CommandHandler("clear_reminders", clear_reminders_command))

    # handle interval commands
    app.add_handler(CommandHandler("show_intervals", show_intervals_command))
    app.add_handler(CommandHandler("set_intervals", set_intervals_command))
    app.add_handler(CommandHandler("reset_intervals", reset_intervals_command))

    # handle dictionary commands
    app.add_handler(CommandHandler("show_dictionary", show_dictionary_command))
    app.add_handler(CommandHandler("choose_dictionary", choose_dictionary_command))
    app.add_handler(CommandHandler("switch_dictionary", switch_dictionary_command))

    # handle invalid commands
    app.add_handler(MessageHandler(filters.COMMAND, invalid_command_handler))

    # ----------------------------------------------------------------

    # run the bot using 'polling'
    app.run_polling()
