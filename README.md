# Oneling Bot

Telegram bot for learning vocabulary.

> **Status:** the public bot is currently offline. You can still run your own instance, see [Running locally](#running-locally).

Send Oneling a word or phrase in the language you're learning. It corrects any mistakes, translates it with examples and a definition, and then reminds you of it at growing intervals, so new words actually stick.

## Features

- **Smart translations:** uses OpenAI (`gpt-4o-mini`) to fix typos and grammar, then gives up to 3 distinct translations, each with an example sentence, plus a definition.
- **Spaced reminders:** reviews each word after 5 minutes, 30 minutes, 2 hours, 12 hours, and 2 days by default. The intervals are fully customizable.
- **11 languages:** English, Dutch, German, French, Spanish, Italian, Russian, Ukrainian, Greek, Arabic, and Japanese. Each dictionary pairs a language with English, in either direction.

## Commands

To add a word, just type it in the chat.

| Command              | Description                                 |
| -------------------- | ------------------------------------------- |
| `/show_reminders`    | Show all reminders                          |
| `/clear_reminders`   | Clear all reminders                         |
| `/show_intervals`    | Show the current reminder intervals         |
| `/set_intervals`     | Set new intervals, e.g. `/set_intervals 5m 30m 2h 12h 2d` |
| `/reset_intervals`   | Reset intervals to the defaults             |
| `/show_dictionary`   | Show the current dictionary                 |
| `/choose_dictionary` | Choose a new dictionary                     |
| `/switch_dictionary` | Swap source and destination languages       |

Changing intervals clears existing reminders, since they were scheduled with the old intervals.

## Tech stack

Python 3.12, python-telegram-bot, OpenAI API, Flask (health check endpoint), Docker

## Running locally

**Prerequisites:** Python 3.12+, a Telegram bot token from [@BotFather](https://t.me/BotFather), and an OpenAI API key.

1. Create a `.env` file in the project root:
   ```bash
   TOKEN=<your-telegram-bot-token>
   OPENAI_API_KEY=<your-openai-api-key>
   ```

2. Install dependencies and start the bot. The optional argument is the port for the health check endpoint (default `80`).
   ```bash
   pip install -r requirements.txt
   python src/main.py 8080
   ```

Or run it with Docker:

```bash
docker build -t oneling-bot .
docker run --env-file .env -p 8080:80 oneling-bot
```

Reminders are stored in memory, so they reset when the bot restarts.
