"""
app.py - Meridian Financial PoC server (scenario 1).

Reader:  GET  /                       article list
         GET  /article/<id>           article page, with a player if audio exists
Editor:  GET  /admin                  audio admin console
API:     POST /api/generate/<id>      generate one article (cache-aware)
         POST /api/regenerate/<id>    force regeneration, ignoring the cache
         POST /api/generate_all       generate every article

Run:     python app.py   ->  http://localhost:5001
"""
import json, os
from flask import Flask, render_template, jsonify
from tts_pipeline import on_publish, load_manifest, MOCK

app = Flask(__name__)
BASE = os.path.dirname(__file__)


def load_articles():
    with open(os.path.join(BASE, "data", "articles.json"), encoding="utf-8") as f:
        return json.load(f)


def find_article(article_id):
    return next((a for a in load_articles() if a["id"] == article_id), None)


# ---------- reader ----------
@app.route("/")
def home():
    return render_template("home.html", articles=load_articles(), manifest=load_manifest())


@app.route("/article/<article_id>")
def article(article_id):
    art = find_article(article_id)
    if not art:
        return "Article not found", 404
    entry = load_manifest().get(article_id, {})
    # The reader page only serves what already exists. It never triggers generation:
    # that happens at publish time, on the editor side.
    audio = f"/static/audio/{entry['file']}" if entry.get("status") == "ready" else None
    return render_template("article.html", art=art, audio=audio, entry=entry)


# ---------- editor ----------
@app.route("/admin")
def admin():
    articles, manifest = load_articles(), load_manifest()
    total_chars = sum(e.get("chars", 0) for e in manifest.values()
                      if e.get("status") == "ready")
    return render_template("admin.html", articles=articles, manifest=manifest,
                           total_chars=total_chars, mock=MOCK)


@app.route("/api/generate/<article_id>", methods=["POST"])
def generate_one(article_id):
    art = find_article(article_id)
    if not art:
        return jsonify({"error": "no such article"}), 404
    return jsonify(on_publish(art["id"], art["title"], art["body"], force=False))


@app.route("/api/regenerate/<article_id>", methods=["POST"])
def regenerate_one(article_id):
    art = find_article(article_id)
    if not art:
        return jsonify({"error": "no such article"}), 404
    return jsonify(on_publish(art["id"], art["title"], art["body"], force=True))


@app.route("/api/generate_all", methods=["POST"])
def generate_all():
    return jsonify({art["id"]: on_publish(art["id"], art["title"], art["body"])
                    for art in load_articles()})


if __name__ == "__main__":
    print(f"Mode: {'MOCK (placeholder tone, zero cost)' if MOCK else 'REAL (ElevenLabs API)'}")
    print("Reader  http://localhost:5001/")
    print("Console http://localhost:5001/admin")
    # Never hardcode debug=True: the Werkzeug debugger is remote code execution
    # for anyone who can reach the port. Opt in explicitly with FLASK_DEBUG=1.
    app.run(port=5001, debug=os.environ.get("FLASK_DEBUG") == "1")
