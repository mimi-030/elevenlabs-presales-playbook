"""
app.py - latency lab server (scenario 2).

GET  /                       lab UI
POST /api/latency/<mode>     mode   = serial | streaming
POST /api/stress/<client>    client = naked  | safe   (?n=10 sets the request count)

Run: python app.py  ->  http://localhost:5002
"""
import os
from flask import Flask, render_template, jsonify, request
from engine import run_latency, run_stress, MOCK

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html", mock=MOCK)


@app.route("/api/latency/<mode>", methods=["POST"])
def latency(mode):
    if mode not in ("serial", "streaming"):
        return jsonify({"error": "mode must be serial|streaming"}), 400
    return jsonify(run_latency(mode))


@app.route("/api/stress/<client>", methods=["POST"])
def stress(client):
    if client not in ("naked", "safe"):
        return jsonify({"error": "client must be naked|safe"}), 400
    n = int(request.args.get("n", 10))
    n = max(2, min(n, 16))          # guardrail: do not let REAL mode burn credits in one click
    return jsonify(run_stress(client, n))


if __name__ == "__main__":
    print(f"Mode: {'MOCK (zero-cost simulation)' if MOCK else 'REAL (ElevenLabs API, uses credits)'}")
    print("Lab http://localhost:5002/")
    app.run(port=5002, debug=os.environ.get("FLASK_DEBUG") == "1")
