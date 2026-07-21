"""
app.py - read-along classroom server (scenario 3).

GET  /                  upload page: audio file, plus a transcript in MOCK mode
POST /api/transcribe    save audio -> transcribe (mock or real) -> save project -> player link
GET  /player/<pid>      student player: karaoke highlight, click to seek, speed, speaker filter

Run: python app.py  ->  http://localhost:5003
"""
import os, json, uuid
from flask import Flask, render_template, request, jsonify
from stt import mock_transcribe, real_transcribe, MOCK

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024      # reject oversized uploads early
BASE = os.path.dirname(__file__)
UPLOADS = os.path.join(BASE, "static", "uploads")
PROJECTS = os.path.join(BASE, "data", "projects")
ALLOWED = {".mp3", ".wav", ".m4a", ".webm", ".ogg", ".mp4", ".flac"}


@app.route("/")
def home():
    return render_template("upload.html", mock=MOCK)


@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    upload = request.files.get("audio")
    if not upload or not upload.filename:
        return jsonify({"error": "Please choose an audio file"}), 400
    ext = os.path.splitext(upload.filename)[1].lower()
    if ext not in ALLOWED:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400

    # The client-supplied filename is discarded entirely; we store under a generated id.
    project_id = uuid.uuid4().hex[:8]
    audio_name = f"{project_id}{ext}"
    os.makedirs(UPLOADS, exist_ok=True)
    os.makedirs(PROJECTS, exist_ok=True)
    upload.save(os.path.join(UPLOADS, audio_name))

    try:
        if MOCK:
            text = request.form.get("transcript", "").strip()
            duration = float(request.form.get("duration", 0) or 0)
            if not text:
                return jsonify({"error": "MOCK mode needs a transcript to lay out"}), 400
            if duration <= 0:
                duration = len(text) * 0.35        # fallback if the browser could not read it
            words = mock_transcribe(text, duration)
        else:
            words = real_transcribe(os.path.join(UPLOADS, audio_name))
    except Exception as exc:
        return jsonify({"error": str(exc)[:200]}), 502

    with open(os.path.join(PROJECTS, f"{project_id}.json"), "w", encoding="utf-8") as fp:
        json.dump({"audio": audio_name, "words": words,
                   "mode": "mock" if MOCK else "real"}, fp, ensure_ascii=False, indent=1)
    return jsonify({"player": f"/player/{project_id}", "words": len(words)})


@app.route("/player/<project_id>")
def player(project_id):
    path = os.path.join(PROJECTS, f"{project_id}.json")
    if not os.path.exists(path):
        return "Project not found", 404
    with open(path, encoding="utf-8") as fp:
        project = json.load(fp)
    speakers = sorted({w.get("speaker", "A") for w in project["words"]})
    return render_template("player.html", proj=project, pid=project_id, speakers=speakers)


if __name__ == "__main__":
    print(f"Mode: {'MOCK (transcript laid out on the timeline, zero cost)' if MOCK else 'REAL (ElevenLabs STT)'}")
    print("Classroom http://localhost:5003/")
    app.run(port=5003, debug=os.environ.get("FLASK_DEBUG") == "1")
