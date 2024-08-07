import sys
import os
import threading

from dotenv import load_dotenv
from flask import Flask, jsonify
from waitress import serve

# load environment variables
load_dotenv()

# get the directory where main.py is located
src_dir = os.path.dirname(os.path.abspath(__file__))

# get the project root directory
project_root = os.path.dirname(src_dir)

# define the lib directory
lib_dir = os.path.join(project_root, "lib")

# add the lib directory to sys.path
sys.path.insert(0, lib_dir)

import bot

# initialize Flask app
app = Flask(__name__)


@app.route("/", methods=["GET"])
def health_check():
    return jsonify(status="UP"), 200


def run_flask():
    port = 80 if len(sys.argv) == 1 else int(sys.argv[1])
    run_serve = lambda: serve(app, host="0.0.0.0", port=port)
    threading.Thread(target=run_serve).start()


def run_bot():
    token = os.environ["TOKEN"]
    bot.run(token)


if __name__ == "__main__":
    run_flask()
    run_bot()
