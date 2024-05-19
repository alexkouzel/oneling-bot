from dotenv import load_dotenv
import threading
import os

import flask_app
import bot

load_dotenv()  # load env variables from .env

if __name__ == "__main__":

    # run flask app on the background (used for health checks)
    threading.Thread(target=lambda: flask_app.main()).start()

    # run telegram bot with a token from env variables
    token = os.environ["TOKEN"]
    bot.main(token)
