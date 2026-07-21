"""
app.py - Patch 1.4 voice batch console (scenario 6).

GET  /                    the batch console
POST /api/run             run the whole batch (unchanged successes are skipped)
POST /api/retry_failed    re-run only the failures, driven by the manifest

Run: python app.py  ->  http://localhost:5006
"""
import os
from flask import Flask, render_template, jsonify
from engine import (run_batch, load_lines, load_manifest, stats,
                    REGISTRY, CHARACTER_NAMES, MOCK, MODEL_ID)

app = Flask(__name__)


@app.route("/")
def console():
    return render_template("console.html",
                           lines=load_lines(), manifest=load_manifest(), s=stats(),
                           registry=REGISTRY, char_names=CHARACTER_NAMES,
                           mock=MOCK, model=MODEL_ID)


@app.route("/api/run", methods=["POST"])
def api_run():
    run_batch()
    return jsonify(stats())


@app.route("/api/retry_failed", methods=["POST"])
def api_retry():
    failed = stats()["failed_ids"]
    if failed:
        run_batch(only_ids=failed)      # manifest-driven retry: the button that matters at scale
    return jsonify(stats())


if __name__ == "__main__":
    print(f"Mode: {'MOCK (placeholder tones, zero cost)' if MOCK else f'REAL (ElevenLabs {MODEL_ID})'}")
    print("Console http://localhost:5006/")
    app.run(port=5006, debug=os.environ.get("FLASK_DEBUG") == "1")
