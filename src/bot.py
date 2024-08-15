import time
import httpx

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

from models import Reminder, Chat, Dictionary, Translation, Example
from translator import translate
from utils import time_to_str, str_to_time

type CallbackArgs = tuple[Update, ContextTypes.DEFAULT_TYPE, list[str]]

type Example = tuple[str, str]

# ----------------------------------------------------------------
#  @constants
# ----------------------------------------------------------------

DEVELOPER_CHAT_ID = 597554184

DEFAULT_REMINDER_INTERVALS = [h * 60 for h in [5, 30, 120, 720, 2880]]

TRANSLATIONS_PER_REMINDER = 3
EXAMPLES_PER_TRANSLATION = 1

MAX_VALUE_LENGTH = 100

PRIMARY_LANGUAGE = "en"

LANGUAGES = {
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "nl": "Dutch",
    "ru": "Russian",
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


def str_dst_values(dst_values: list[str]) -> str:
    return " / ".join(dst_values)


def str_translation(translation: Translation) -> str:
    dst_str = str_dst_values(translation.get_dst_values())
    return f"<b>{translation.src}</b> - {dst_str}"


def str_examples(examples: list[Example]) -> str:
    result = [
        f"<b>{idx + 1}. {example.src}</b>\nTranslation: {example.dst}\n"
        for idx, example in enumerate(examples)
    ]
    result = "\n".join(result)
    return result


# ----------------------------------------------------------------
#  @default
# ----------------------------------------------------------------


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
        f"Intervals are reset to default values: {str_intervals(DEFAULT_REMINDER_INTERVALS)}"
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

    reminders = repository.get_active_reminders(chat.id)

    if not reminders:
        await update.message.reply_text("You have no active reminders")
        return

    reminders = [
        f"{idx + 1}. {str_translation(reminder.translation)}"
        for idx, reminder in enumerate(reminders)
    ]
    reminders = "\n".join(reminders)

    await update.message.reply_text(reminders, parse_mode="HTML")


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

    # If the reminder already exists, reset it
    reminder = repository.get_reminder(chat.id, value, chat.dictionary)

    if reminder:
        reminder.last_at = time.time()
        reminder.left = len(chat.reminder_intervals)

        repository.update_reminder(chat.id, reminder)

    # If the reminder does not exist, create a new one
    else:
        reminder = await create_reminder(update, chat, value)

        if not reminder:
            await update.message.reply_text(
                f'The value "{value}" is not valid. Try again'
            )
            return

        repository.save_reminder(chat.id, reminder)

    await send_reminder(context, chat, reminder)


async def create_reminder(update: Update, chat: Chat, value: str):
    translation = translate(
        value,
        chat.dictionary.src,
        chat.dictionary.dst,
        TRANSLATIONS_PER_REMINDER,
        EXAMPLES_PER_TRANSLATION,
    )

    if not translation:
        return None

    id = chat.reminder_next_id

    last_at = time.time()
    left = len(chat.reminder_intervals)

    return Reminder(id, last_at, left, translation, chat.dictionary)


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
    translation_str = str_translation(reminder.translation)
    left_str = str_reminder_left(chat, reminder)

    return f"{translation_str}\n\n{left_str}"


def str_reminder_left(chat: Chat, reminder: Reminder) -> str:
    if reminder.left == 0:
        return "** last reminder **"

    next_reminder_str = time_to_str(chat.get_reminder_interval(reminder))

    return "Next reminder in: {}\nReminders left: {}/{}".format(
        next_reminder_str, reminder.left, len(chat.reminder_intervals)
    )


def reminder_keyboard(reminder: Reminder) -> InlineKeyboardMarkup:
    buttons = []

    # Examples button
    if reminder.has_examples:
        data = f"examples|{reminder.id}"
        btn = InlineKeyboardButton("Examples", callback_data=data)
        buttons.append(btn)

    # Stop button
    if reminder.left > 0:
        data = f"stop|{reminder.id}"
        btn = InlineKeyboardButton("Stop Reminder", callback_data=data)
        buttons.append(btn)

    return InlineKeyboardMarkup(to_2d(buttons))


async def stop_callback(args: CallbackArgs):
    await reminder_callback(
        args,
        repository.remove_reminder,
        lambda reminder: f'Reminder "{reminder.translation.src}" is stopped',
    )


async def examples_callback(args: CallbackArgs):
    await reminder_callback(
        args,
        repository.get_reminder,
        lambda reminder: str_examples(reminder.translation.get_examples()),
    )


async def reminder_callback(
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


# ----------------------------------------------------------------
#  @reminder_caller
# ----------------------------------------------------------------


async def call_reminder(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()

    for chat in repository.get_all_chats():
        for reminder in repository.get_active_reminders(chat.id):

            reminder_interval = chat.get_reminder_interval(reminder)
            time_to_remind = (now - reminder.last_at) > reminder_interval

            if time_to_remind:
                repository.handle_reminder_call(chat.id, reminder.id)
                await send_reminder(context, chat, reminder)

                break


# ----------------------------------------------------------------
#  @common_handlers
# ----------------------------------------------------------------


async def non_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = update.message.text

    if len(value) > MAX_VALUE_LENGTH:
        update.message.reply_text("The word or phrase is too long. Try again")

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
        case _:
            return


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        return

    if isinstance(context.error, httpx.ReadError):
        return

    logger.error("An error occurred: ", exc_info=context.error)

    # Notify the developer about the error
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

    # Call reminders every 5 seconds
    app.job_queue.run_repeating(call_reminder, interval=5)

    # ----------------------------------------------------------------
    # --- Common Handlers ---

    # Handle errors during bot operation
    app.add_error_handler(error_handler)

    # Handle callback from keyboards
    app.add_handler(CallbackQueryHandler(keyboard_handler))

    # Handle non-command messages
    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), non_command_handler)
    )

    # ----------------------------------------------------------------
    # --- Commands ---

    # Handle default commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    # Handle reminder commands
    app.add_handler(CommandHandler("show_reminders", show_reminders_command))
    app.add_handler(CommandHandler("clear_reminders", clear_reminders_command))

    # Handle interval commands
    app.add_handler(CommandHandler("show_intervals", show_intervals_command))
    app.add_handler(CommandHandler("set_intervals", set_intervals_command))
    app.add_handler(CommandHandler("reset_intervals", reset_intervals_command))

    # Handle dictionary commands
    app.add_handler(CommandHandler("show_dictionary", show_dictionary_command))
    app.add_handler(CommandHandler("choose_dictionary", choose_dictionary_command))
    app.add_handler(CommandHandler("switch_dictionary", switch_dictionary_command))

    # Handle invalid commands
    app.add_handler(MessageHandler(filters.COMMAND, invalid_command_handler))

    # ----------------------------------------------------------------

    # Run the bot using 'polling'
    app.run_polling()
