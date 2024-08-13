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

from models import Reminder, Chat, Dictionary
from utils import time_to_str, str_to_time

from linguee.api import translations

type CallbackArgs = tuple[Update, ContextTypes.DEFAULT_TYPE, list[str]]

# ----------------------------------------------------------------
#  @constants
# ----------------------------------------------------------------

DEFAULT_REMINDER_INTERVALS = [h * 60 for h in [5, 30, 120, 720, 2880]]

TRANSLATIONS_PER_REMINDER = 3
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

# ----------------------------------------------------------------
#  @utils
# ----------------------------------------------------------------


def get_chat(update: Update) -> Chat:
    return repository.get_chat(update.effective_chat.id)


# ----------------------------------------------------------------
#  @default
# ----------------------------------------------------------------


def get_help_message(chat: Chat):
    return f"""

I can help you to remember words and phrases in different languages by sending you reminders at specified intervals.

<b>🔔  To manage reminders:</b>
/show_reminders - show all reminders
/clear_reminders - clear all reminders

To set a new reminder, just type the word or phrase you want to remember.

<b>⏰  To manage intervals:</b>
/show_intervals - show current intervals
/set_intervals - set new intervals
/reset_intervals - reset intervals to default values

Note: If you change intervals, all existing reminders will be cleared because they use the old intervals.

<b>🌐  To manage your dictionary:</b>
/show_dictionary - show current dictionary
/choose_dictionary - choose new dictionary

<b>⚙️  Current settings:</b>
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


async def show_dictionary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update)

    await update.message.reply_text(str_dictionary(chat.dictionary))


async def choose_dictionary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dictionaries = [
        Dictionary(PRIMARY_LANGUAGE, language)
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

    keyboard = InlineKeyboardMarkup(
        [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    )

    await update.message.reply_text(
        "Please choose the dictionary you want to use:",
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
        return await update.message.reply_text(set_intervals_usage)

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
        return await update.message.reply_text("You have no reminders")

    reminders = [
        f"{reminder.src} - {reminder.dst}" for reminder in chat.reminders.values()
    ]
    reminders = "\n".join(reminders)

    await update.message.reply_text(reminders)


async def clear_reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    repository.clear_reminders(chat_id)

    await update.message.reply_text("You no longer have any reminders")


# ----------------------------------------------------------------
#  @reminder_creation
# ----------------------------------------------------------------


async def create_reminder(update: Update, chat: Chat, value: str):
    lemmas = await translations(value, chat.dictionary.src, chat.dictionary.dst)

    if not lemmas:
        await update.message.reply_text(f'The value "{value}" is not found. Try again')
        return None

    idx = chat.reminder_next_id

    last_at = time.time()
    left = len(chat.reminder_intervals)

    src = lemmas_src(lemmas)
    dst = lemmas_dst(lemmas)

    examples = lemmas_examples(lemmas)

    return Reminder(idx, last_at, left, src, dst, examples)


async def create_reminder_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, value: str
):
    chat = get_chat(update)

    reminder = await create_reminder(update, chat, value)

    if not reminder:
        return None

    repository.save_reminder(chat.id, reminder)

    await send_reminder(context, chat, reminder)


def lemmas_src(lemmas):
    return lemmas[0].text


def lemmas_dst(lemmas):
    translations = set()

    for lemma in lemmas:
        for translation in lemma.translations:
            translations.add(translation.text)

    translations = list(translations)[:TRANSLATIONS_PER_REMINDER]

    return " / ".join(translations)


def lemmas_examples(lemmas):
    examples = [
        (example.src, example.dst)
        for lemma in lemmas
        for translation in lemma.translations
        for example in translation.examples
    ]
    return examples[:EXAMPLES_PER_REMINDER]


# ----------------------------------------------------------------
#  @reminder_sending
# ----------------------------------------------------------------


async def send_reminder(
    context: ContextTypes.DEFAULT_TYPE, chat: Chat, reminder: Reminder
):
    text = str_reminder(chat, reminder)
    keyboard = reminder_keyboard(reminder)

    await context.bot.send_message(chat_id=chat.id, text=text, reply_markup=keyboard)


def str_reminder(chat: Chat, reminder: Reminder) -> str:
    left = str_reminder_left(chat, reminder)

    return f"{reminder.src} - {reminder.dst}\n\n{left}"


def str_reminder_left(chat: Chat, reminder: Reminder) -> str:
    if reminder.left == 0:
        return "** last reminder **"

    next_reminder = time_to_str(chat.get_reminder_interval(reminder))

    return "Next reminder in: {}\nReminders left: {} / {}".format(
        next_reminder, reminder.left, len(chat.reminder_intervals)
    )


def reminder_keyboard(reminder: Reminder) -> InlineKeyboardMarkup:
    if reminder.left == 0:
        return None

    stop_btn = InlineKeyboardButton("Stop", callback_data=f"stop|{reminder.id}")

    buttons = [stop_btn]

    if reminder.examples:
        examples_btn = InlineKeyboardButton(
            "Examples", callback_data=f"examples|{reminder.id}"
        )
        buttons.append(examples_btn)

    return InlineKeyboardMarkup([buttons])


async def reminder_callback(
    args: CallbackArgs, reminder_action: callable, response_message: callable
):
    (update, context, data) = args

    chat_id = update.effective_chat.id
    reminder_id = int(data[1])

    reminder = reminder_action(chat_id, reminder_id)

    if not reminder:
        return await context.bot.send_message(chat_id, "Reminder is not found")

    message = response_message(reminder)

    await context.bot.send_message(chat_id, message)


async def stop_callback(args: CallbackArgs):
    await reminder_callback(
        args,
        repository.remove_reminder,
        lambda reminder: f'Reminder "{reminder.src}" is stopped',
    )


async def examples_callback(args: CallbackArgs):
    await reminder_callback(
        args,
        repository.get_reminder,
        lambda reminder: "\n".join(
            [
                f"{idx + 1}. {dst} - {src}\n"
                for idx, (src, dst) in enumerate(reminder.examples)
            ]
        ),
    )


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
        case _:
            return


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        raise context.error
    except Conflict:
        # ignore conflicts as they occur during redeploys
        return


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

    # handle invalid commands
    app.add_handler(MessageHandler(filters.COMMAND, invalid_command_handler))

    # ----------------------------------------------------------------

    # run the bot using 'polling'
    app.run_polling()
