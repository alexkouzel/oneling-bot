from flask import Flask, jsonify
from waitress import serve

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health_check():
    return jsonify(status="UP"), 200


def main():
    serve(app, host="0.0.0.0", port=80)
