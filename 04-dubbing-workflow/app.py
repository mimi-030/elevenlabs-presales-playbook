"""
app.py - dubbing review board server (scenario 4).

GET  /                    the three-column review board
GET  /api/lines           every line (the UI polls this every 1.2s, so a line in
                          REGENERATING flips to IN REVIEW on its own)
POST /api/action/<id>     {action, actor, role, text?, version?, comment?}
                          403 = refused by the rule table, 409 = optimistic lock conflict

Run: python app.py  ->  http://localhost:5004
"""
import os
from flask import Flask, render_template, jsonify, request
from engine import (seed_if_empty, all_lines, apply_action,
                    ConflictError, ForbiddenError, MOCK)

app = Flask(__name__)
seed_if_empty()


@app.route("/")
def board():
    return render_template("board.html", mock=MOCK)


@app.route("/api/lines")
def lines():
    return jsonify(all_lines())


@app.route("/api/action/<line_id>", methods=["POST"])
def action(line_id):
    payload = request.get_json(force=True)
    try:
        line = apply_action(line_id, payload["action"],
                            payload.get("actor", "?"), payload.get("role", "?"),
                            new_text=payload.get("text"),
                            expected_version=payload.get("version"),
                            comment=payload.get("comment"))
        return jsonify(line)
    except ForbiddenError as exc:         # the rule table said no
        return jsonify({"error": str(exc)}), 403
    except ConflictError as exc:          # the optimistic lock said you are behind
        return jsonify({"error": str(exc)}), 409
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404


if __name__ == "__main__":
    print(f"Mode: {'MOCK (placeholder tone; pitch changes when a line is edited)' if MOCK else 'REAL (ElevenLabs TTS)'}")
    print("Review board http://localhost:5004/")
    app.run(port=5004, debug=os.environ.get("FLASK_DEBUG") == "1")
