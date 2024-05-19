from flask import Flask, jsonify
from waitress import serve

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health_check():
    return jsonify(status="UP"), 200


def main(port: int):
    serve(app, host="0.0.0.0", port=port)
