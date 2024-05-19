from dotenv import load_dotenv
import threading
import os

import flask_app
import bot
import sys

load_dotenv()  # load env variables from .env

if __name__ == "__main__":
    port = 80 if len(sys.argv) == 1 else int(sys.argv[1])

    # run flask app on the background (used for health checks)
    threading.Thread(target=lambda: flask_app.main(port)).start()

    # run telegram bot with a token from env variables
    token = os.environ["TOKEN"]
    bot.main(token)
