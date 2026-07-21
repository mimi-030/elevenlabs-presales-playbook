"""
engine.py - scenario 6: the game localization batch engine.

    CSV of lines -> look up the voice in REGISTRY -> SafeClient batch -> audio + manifest

Three things this is built to prove:

  1. A voice is an asset. (character, language) -> voice_id lives in a lookup table
     driven by environment variables, not scattered through the code.
  2. One bad line does not kill the batch. A missing voice mapping or an API error is
     recorded and the run continues, and the manifest makes "retry only the failures"
     a one-click operation.
  3. A batch protects itself. The SafeClient from scenario 2 is reused as is: a batch
     job is the single easiest way to exhaust your own rate limit.
"""
import os, csv, json, time, math, struct, random, threading

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
MODEL_ID = os.environ.get("ELEVEN_MODEL", "eleven_multilingual_v2")  # pre-baked: quality model
MOCK = API_KEY is None
BASE = os.path.dirname(__file__)
AUDIO_DIR = os.path.join(BASE, "static", "audio")
MANIFEST_PATH = os.path.join(BASE, "data", "manifest.json")
CSV_PATH = os.path.join(BASE, "data", "lines.csv")

# ---------- 1. the voice asset registry ----------
# (character, language) -> voice_id. Pick voices in the Voice Library, put their ids in
# environment variables, and nobody has to touch the code. Separating the asset from the
# program is the design decision worth showing.
_SAMPLE_VOICE = "JBFqnCBsd6RMkjVDRZzb"               # ElevenLabs sample voice, replace it
REGISTRY = {
    ("hero", "en"):     os.environ.get("VOICE_HERO_EN", _SAMPLE_VOICE),
    ("hero", "es"):     os.environ.get("VOICE_HERO_ES", _SAMPLE_VOICE),
    ("merchant", "en"): os.environ.get("VOICE_MERCHANT_EN", _SAMPLE_VOICE),
    ("merchant", "es"): os.environ.get("VOICE_MERCHANT_ES", _SAMPLE_VOICE),
    # Note: the CSV deliberately contains a "ghost" line with no entry here, which is
    # how the "one failure does not kill the batch" behaviour becomes visible.
}
CHARACTER_NAMES = {"hero": "Rin the Hero",
                   "merchant": "Gus the Merchant",
                   "ghost": "Ghost (not registered)"}


# ---------- TTS layer (mock and real share one interface) ----------
class MockTTS:
    """Fake API. Each voice_id and language gets its own pitch, so different characters
    audibly sound different. Capacity is limited, so retries are exercised too."""

    def __init__(self, capacity=3):
        self.capacity, self.active = capacity, 0
        self.lock = threading.Lock()

    def synth(self, text, voice_id, lang):
        with self.lock:
            if self.active >= self.capacity:
                raise RuntimeError("429")
            self.active += 1
        try:
            time.sleep(0.2 + len(text) * 0.01)
            rate, seconds = 22050, 0.8 + len(text) * 0.05
            freq = 220 + (hash((voice_id, lang)) % 400)
            frames = bytearray()
            total = int(rate * seconds)
            for i in range(total):
                fade = min(1, i / 1500, (total - i) / 1500)
                frames += struct.pack("<h",
                    int(11000 * fade * math.sin(2 * math.pi * freq * i / rate)))
            return bytes(frames), "wav", rate
        finally:
            with self.lock:
                self.active -= 1


class RealTTS:
    def synth(self, text, voice_id, lang):
        import requests
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
            json={"text": text, "model_id": MODEL_ID},
            headers={"xi-api-key": API_KEY}, timeout=60)
        if r.status_code == 429:
            raise RuntimeError("429")
        if r.status_code != 200:
            raise RuntimeError(f"API {r.status_code}: {r.text[:120]}")
        return r.content, "mp3", None


# ---------- 3. the SafeClient from scenario 2, reused unchanged ----------
class SafeClient:
    """Concurrency gate -> queue -> backoff retry, exactly as in scenario 2."""

    def __init__(self, tts, max_concurrent=3, max_retries=3):
        self.tts = tts
        self.gate = threading.Semaphore(max_concurrent)
        self.retries = max_retries

    def synth(self, text, voice_id, lang):
        with self.gate:                                   # queue rather than drop
            for attempt in range(self.retries + 1):
                try:
                    data, ext, _ = self.tts.synth(text, voice_id, lang)
                    return data, ext, attempt + 1
                except RuntimeError as exc:
                    if "429" not in str(exc) or attempt == self.retries:
                        raise
                    time.sleep((2 ** attempt) * 0.2 + random.uniform(0, 0.2))


# ---------- CSV and manifest ----------
def load_lines():
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)


# ---------- 2. the batch itself: one failure does not stop the run ----------
def run_batch(only_ids=None) -> dict:
    """only_ids=None runs everything, skipping lines that already succeeded and have
    not changed. only_ids=[...] runs just those lines, which is how retry works.

    Every line is wrapped in its own try. One broken line is recorded and the run
    continues; it does not take 300,000 other lines down with it.
    """
    tts = MockTTS() if MOCK else RealTTS()
    client = SafeClient(tts, max_concurrent=3)
    manifest = load_manifest()
    lines = load_lines()
    if only_ids:
        lines = [line for line in lines if line["line_id"] in set(only_ids)]

    def work(line):
        line_id = line["line_id"]
        previous = manifest.get(line_id, {})
        # Already generated and the text has not changed: skip. Same saving as scenario 1.
        if only_ids is None and previous.get("status") == "ok" \
                and previous.get("text") == line["text"]:
            previous["last_action"] = "skipped"
            manifest[line_id] = previous
            return

        entry = {"line_id": line_id, "character": line["character"], "lang": line["lang"],
                 "text": line["text"], "chars": len(line["text"])}
        voice_id = REGISTRY.get((line["character"], line["lang"]))
        if voice_id is None:                    # a data problem: record it and move on
            entry.update({"status": "failed", "error": "no voice mapping in REGISTRY",
                          "last_action": "failed"})
            manifest[line_id] = entry
            return
        try:
            data, ext, attempts = client.synth(line["text"], voice_id, line["lang"])
            filename = f"{line_id}_{line['lang']}.{ext}"
            with open(os.path.join(AUDIO_DIR, filename), "wb") as f:
                f.write(data)
            entry.update({"status": "ok", "file": filename, "voice_id": voice_id,
                          "attempts": attempts, "last_action": "generated",
                          "at": time.strftime("%m/%d %H:%M")})
        except Exception as exc:                # API failures are treated the same way
            entry.update({"status": "failed", "error": str(exc)[:150],
                          "last_action": "failed"})
        manifest[line_id] = entry

    threads = [threading.Thread(target=work, args=(line,)) for line in lines]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    save_manifest(manifest)
    return manifest


# ---------- statistics for the console ----------
def stats():
    manifest, lines = load_manifest(), load_lines()
    by_language = {}
    for line in lines:
        bucket = by_language.setdefault(line["lang"],
                                        {"total": 0, "ok": 0, "failed": 0, "chars": 0})
        bucket["total"] += 1
        entry = manifest.get(line["line_id"], {})
        if entry.get("status") == "ok":
            bucket["ok"] += 1
            bucket["chars"] += entry.get("chars", 0)
        elif entry.get("status") == "failed":
            bucket["failed"] += 1
    failed_ids = [lid for lid, e in manifest.items() if e.get("status") == "failed"]
    total_chars = sum(e.get("chars", 0) for e in manifest.values()
                      if e.get("status") == "ok")
    return {"langs": by_language, "failed_ids": failed_ids, "total_chars": total_chars}
