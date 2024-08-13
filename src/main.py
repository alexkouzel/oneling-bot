import sys
import os
import threading

from waitress import serve
from dotenv import load_dotenv
from flask import Flask, jsonify

import bot

# load environment variables
load_dotenv()

# initialize Flask app
app = Flask(__name__)


@app.route("/", methods=["GET"])
def health_check():
    return jsonify(status="UP"), 200


def run_flask_in_background() -> None:
    port = 80 if len(sys.argv) == 1 else int(sys.argv[1])
    run_serve = lambda: serve(app, host="0.0.0.0", port=port)
    threading.Thread(target=run_serve).start()


def run_bot_polling() -> None:
    token = os.environ["TOKEN"]
    bot.run_polling(token)


if __name__ == "__main__":
    run_flask_in_background()
    run_bot_polling()
