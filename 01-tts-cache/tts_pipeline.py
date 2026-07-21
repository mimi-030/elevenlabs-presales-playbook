"""
tts_pipeline.py - the core pipeline for scenario 1.

    publish event -> normalize text -> content-hash cache -> generate -> save + manifest

Two modes:
  MOCK (default) - no ELEVEN_KEY in the environment. Generates a short placeholder
                   WAV so the whole flow is exercisable at zero cost.
  REAL           - ELEVEN_KEY is set. Calls the ElevenLabs TTS API and saves an mp3.

The design decision worth pointing at during a demo: audio is generated when an
article is *published*, not when a reader opens it. One generation serves every
future reader, and an unchanged article never costs anything a second time.
"""
import os, re, json, time, wave, math, random, struct, hashlib

# ---------- configuration ----------
# Minimal dependency-free .env loader, so the repo runs with `pip install flask`.
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _fh:
        for _line in _fh:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _value = _line.partition("=")
                if _value.strip():
                    os.environ.setdefault(_key.strip(), _value.strip())

API_KEY = os.environ.get("ELEVEN_KEY") or None
VOICE_ID = os.environ.get("ELEVEN_VOICE", "JBFqnCBsd6RMkjVDRZzb")   # ElevenLabs sample voice
MODEL_ID = os.environ.get("ELEVEN_MODEL", "eleven_multilingual_v2")  # pre-generated: quality over speed
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "static", "audio")
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "data", "manifest.json")
MOCK = API_KEY is None            # presence of a key decides which path we take


# ---------- manifest: the data behind the audio admin console ----------
def load_manifest() -> dict:
    """Return the current audio state of every article. Empty dict on first run."""
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict) -> None:
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)


# ---------- 1. text preprocessing: financial copy is not TTS-ready ----------
DIGIT_WORDS = ["zero", "one", "two", "three", "four",
               "five", "six", "seven", "eight", "nine"]


def normalize(text: str) -> str:
    """Rewrite the things a TTS model reliably gets wrong into a spoken form.

    Doing this client-side is a deliberate choice: we fix what we can control
    instead of hoping the model guesses right. That is the point to make in a demo.
    """
    # Stock tickers: "(2330)" -> ", ticker two three three zero," so it is read
    # digit by digit rather than as the number two thousand three hundred thirty.
    text = re.sub(
        r"\s*\((\d{4,6})\)",
        lambda m: ", ticker " + " ".join(DIGIT_WORDS[int(d)] for d in m.group(1)) + ",",
        text,
    )
    text = re.sub(r"(\d)%", r"\1 percent", text)                  # 15% -> 15 percent
    text = re.sub(r"\$(\d+(?:\.\d+)?)B\b", r"\1 billion dollars", text)
    text = re.sub(r"\$(\d+(?:\.\d+)?)M\b", r"\1 million dollars", text)
    for quarter, spoken in (("Q1", "first quarter"), ("Q2", "second quarter"),
                            ("Q3", "third quarter"), ("Q4", "fourth quarter")):
        text = text.replace(quarter, spoken)
    text = text.replace("H1", "first half").replace("H2", "second half")
    text = text.replace("FY", "fiscal year ")
    return text


# ---------- 2. content fingerprint: never pay twice for identical text ----------
def content_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ---------- 3. generation (two interchangeable backends) ----------
def _mock_generate(article_id: str, text: str) -> str:
    """MOCK: write a short placeholder tone.

    Pitch is derived from the article id so every article sounds distinct, and
    length grows with character count so a long article visibly produces a longer
    file. The player then has something real to play.
    """
    path = os.path.join(AUDIO_DIR, f"{article_id}.wav")
    rate = 22050
    seconds = min(2.0 + len(text) / 400, 6.0)              # longer text, longer file, capped at 6s
    freq = 300 + (int(content_hash(article_id + text)[:4], 16) % 300)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        total_frames = int(rate * seconds)
        frames = bytearray()
        for i in range(total_frames):
            fade = min(1, i / 2000, (total_frames - i) / 2000)   # fade in/out so it is not harsh
            value = int(12000 * fade * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<h", value)
        w.writeframes(bytes(frames))
    return f"{article_id}.wav"


def _real_generate(article_id: str, text: str) -> str:
    """REAL: call the ElevenLabs TTS API, with retry and exponential backoff."""
    import requests                                          # only needed in REAL mode
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128"
    body = {"text": text, "model_id": MODEL_ID,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    for attempt in range(4):                                 # 1 initial call + 3 retries
        response = requests.post(url, json=body,
                                 headers={"xi-api-key": API_KEY}, timeout=60)
        # Check the status code before writing the file. A non-200 body written to
        # disk becomes a valid-looking file that will not play, and the failure only
        # surfaces later in front of a reader.
        if response.status_code == 200:
            path = os.path.join(AUDIO_DIR, f"{article_id}.mp3")
            with open(path, "wb") as f:
                f.write(response.content)
            return f"{article_id}.mp3"
        if response.status_code == 429 and attempt < 3:      # rate limited: wait longer each time
            time.sleep((2 ** attempt) * 0.5 + random.uniform(0, 0.5))   # backoff + jitter
            continue
        raise RuntimeError(f"API {response.status_code}: {response.text[:200]}")
    raise RuntimeError("failed after retries")


# ---------- 4. public entry point ----------
def on_publish(article_id: str, title: str, text: str, force: bool = False) -> dict:
    """Call this when an article is published, or when an editor clicks Generate.

    Returns the latest manifest entry for that article.
    """
    manifest = load_manifest()
    fingerprint = content_hash(text)
    entry = manifest.get(article_id, {})

    # Cache check: same fingerprint, file still present -> return without spending anything.
    if not force and entry.get("hash") == fingerprint and entry.get("status") == "ready":
        entry["last_action"] = "skipped (unchanged)"
        manifest[article_id] = entry
        save_manifest(manifest)
        return entry

    manifest[article_id] = {"title": title, "hash": fingerprint, "status": "generating",
                            "chars": len(text), "mode": "mock" if MOCK else "real"}
    save_manifest(manifest)
    try:
        spoken_text = normalize(text)
        filename = _mock_generate(article_id, spoken_text) if MOCK \
            else _real_generate(article_id, spoken_text)
        manifest[article_id].update({"status": "ready", "file": filename,
                                     "generated_at": time.strftime("%m/%d %H:%M"),
                                     "last_action": "generated"})
    except Exception as exc:
        # Record the failure instead of swallowing it. A silent failure here means
        # an article ships with no audio and nobody notices until a reader complains.
        manifest[article_id].update({"status": "failed", "error": str(exc)[:200],
                                     "last_action": "failed"})
    save_manifest(manifest)
    return manifest[article_id]
