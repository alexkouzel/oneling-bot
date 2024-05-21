from dotenv import load_dotenv
from flask import Flask, jsonify
from waitress import serve
import oneling.bot
import threading
import sys
import os

# load bot token from .env
load_dotenv()
token = os.environ["TOKEN"]

# init flask app (for health checks)
app = Flask(__name__)


@app.route("/", methods=["GET"])
def health_check():
    return jsonify(status="UP"), 200


def run_flask():
    serve(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    port = 80 if len(sys.argv) == 1 else int(sys.argv[1])

    # run flask app (for health checks)
    threading.Thread(target=run_flask).start()

    # run telegram bot
    oneling.bot.run(token)
