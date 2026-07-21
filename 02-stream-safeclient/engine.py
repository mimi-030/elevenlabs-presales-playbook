"""
engine.py - the experiment engine for scenario 2.

Experiment A (latency)   : serial pipeline vs sentence-level streaming pipeline,
                           measuring TTFB (time to first audio).
Experiment B (rate limit): a naked client vs a SafeClient that adds a concurrency
                           gate, an implicit queue, and backoff retry.

Two modes:
  MOCK (default, no ELEVEN_KEY) - a fake API with simulated latency and a hard
                                  capacity limit. Zero cost, reproducible behaviour.
  REAL (ELEVEN_KEY set)         - calls ElevenLabs. The latency experiment uses the
                                  streaming endpoint so the TTFB number is measured,
                                  not simulated.
"""
import os, time, random, threading

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
VOICE_ID = os.environ.get("ELEVEN_VOICE", "JBFqnCBsd6RMkjVDRZzb")
MOCK = API_KEY is None

# A simulated LLM reply from an AI companion app, emitted token by token.
# Sentences are cut at terminal punctuation.
TOKENS = ["It", "'s", " okay", ",", " I", "'m", " right", " here", " with", " you", ".",
          " Tell", " me", " what", " happened", " today", ".",
          " Whatever", " it", " is", ",", " I", " want", " to", " hear", " all",
          " of", " it", "."]
TOKEN_DELAY = 0.06          # gap between tokens, i.e. simulated LLM streaming speed
SENTENCE_END = (".", "?", "!")


# ---------- TTS layer (mock and real share one interface) ----------
class FakeTTS:
    """Fake API with a capacity limit (raises 429 above it) and realistic latency.

    Thread-safe: several worker threads hit it at once in both experiments.
    """

    def __init__(self, capacity=3):
        self.capacity, self.active = capacity, 0
        self.lock = threading.Lock()

    def synth(self, text, model="flash"):
        with self.lock:
            if self.active >= self.capacity:
                raise RuntimeError("429")
            self.active += 1
        try:
            # flash: fast, meant for realtime. quality: slower, meant for pre-generation.
            time.sleep((0.15 + len(text) * 0.004) if model == "flash"
                       else (0.5 + len(text) * 0.012))
            return {"chars": len(text)}
        finally:
            with self.lock:
                self.active -= 1

    def synth_stream_first_chunk(self, text):
        """Simulate streaming: the first audio chunk arrives after a short startup
        delay, well before the whole sentence has been synthesised."""
        with self.lock:
            if self.active >= self.capacity:
                raise RuntimeError("429")
            self.active += 1
        try:
            time.sleep(0.18)                       # first chunk arrives
            first_chunk_at = time.time()
            time.sleep(len(text) * 0.003)          # remaining chunks stream in while playing
            return first_chunk_at
        finally:
            with self.lock:
                self.active -= 1


class RealTTS:
    """The real API.

    The stress test deliberately uses very short text to keep credit usage low.
    The latency test uses requests(stream=True) so TTFB is genuinely measured.
    """

    def synth(self, text, model="flash"):
        import requests
        model_id = "eleven_flash_v2_5" if model == "flash" else "eleven_multilingual_v2"
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_22050_32",
            json={"text": text, "model_id": model_id},
            headers={"xi-api-key": API_KEY}, timeout=60)
        if r.status_code == 429:
            raise RuntimeError("429")
        if r.status_code != 200:
            raise RuntimeError(f"API {r.status_code}")
        return {"chars": len(text)}

    def synth_stream_first_chunk(self, text):
        import requests
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream?output_format=mp3_22050_32",
            json={"text": text, "model_id": "eleven_flash_v2_5"},
            headers={"xi-api-key": API_KEY}, stream=True, timeout=60)
        if r.status_code == 429:
            raise RuntimeError("429")
        if r.status_code != 200:
            raise RuntimeError(f"API {r.status_code}")
        first_chunk_at = None
        for chunk in r.iter_content(chunk_size=2048):
            if chunk and first_chunk_at is None:
                first_chunk_at = time.time()       # the moment the first chunk lands = TTFB
        return first_chunk_at


def make_tts():
    return FakeTTS() if MOCK else RealTTS()


# ---------- Experiment A: latency comparison ----------
def run_latency(mode: str) -> dict:
    """Run one pipeline and return its timeline events plus the measured TTFB.

    serial    - wait for the full LLM response, synthesise it in one call, then play.
                This is the shape most teams start with.
    streaming - cut the LLM output into sentences as tokens arrive and send each
                sentence to the streaming endpoint immediately.
    """
    tts, t0 = make_tts(), time.time()
    events, now = [], lambda: round(time.time() - t0, 3)
    first_audio = None

    if mode == "serial":
        start = now()
        full_text = "".join(TOKENS)
        for _ in TOKENS:                            # wait for the LLM to finish everything
            time.sleep(TOKEN_DELAY)
        events.append({"type": "llm", "label": "LLM full response", "start": start, "end": now()})
        start = now()
        tts.synth(full_text, model="quality")       # and it is usually the slow model, too
        first_audio = now()
        events.append({"type": "tts", "label": "TTS full response", "start": start, "end": first_audio})

    else:  # streaming - the sentence buffer is the whole trick
        buffer, sentence_index = "", 0
        lock, threads = threading.Lock(), []

        def speak(sentence, index):
            nonlocal first_audio
            started = now()
            chunk_at = tts.synth_stream_first_chunk(sentence)
            audio_at = round(chunk_at - t0, 3)
            with lock:
                if first_audio is None or audio_at < first_audio:
                    first_audio = audio_at
                # list.append is atomic in CPython, but keeping it under the lock
                # keeps the invariant obvious to the next reader.
                events.append({"type": "tts", "label": f"sentence {index} TTS (streamed)",
                               "start": started, "end": now()})

        llm_start = now()
        for token in TOKENS:
            time.sleep(TOKEN_DELAY)
            buffer += token
            if buffer.endswith(SENTENCE_END):
                sentence_index += 1
                # Hand the sentence to a worker thread. The LLM loop does not wait:
                # it keeps emitting the next sentence while this one is being spoken.
                thread = threading.Thread(target=speak, args=(buffer, sentence_index))
                thread.start()
                threads.append(thread)
                buffer = ""
        events.append({"type": "llm", "label": "LLM streaming (overlaps TTS)",
                       "start": llm_start, "end": now()})
        for thread in threads:
            thread.join()

    total = now()
    events.sort(key=lambda e: e["start"])
    return {"mode": mode, "ttfb": first_audio, "total": total, "events": events, "mock": MOCK}


# ---------- Experiment B: rate-limit stress test ----------
class SafeClient:
    """Three layers of protection:

    1. concurrency gate (semaphore) - never exceed what the account can take
    2. queueing               - a blocked caller waits instead of being dropped
    3. backoff + jitter retry - a 429 that slips through is absorbed, not surfaced
    """

    def __init__(self, tts, max_concurrent=3, max_retries=3):
        self.tts = tts
        self.gate = threading.Semaphore(max_concurrent)
        self.retries = max_retries

    def request(self, text):
        attempts, waited = 0, 0.0
        with self.gate:                              # blocking acquire = the queue
            for attempt in range(self.retries + 1):
                attempts += 1
                try:
                    self.tts.synth(text, model="flash")
                    return {"ok": True, "attempts": attempts, "waited": round(waited, 2)}
                except RuntimeError:
                    if attempt == self.retries:
                        return {"ok": False, "attempts": attempts, "waited": round(waited, 2)}
                    delay = (2 ** attempt) * 0.15 + random.uniform(0, 0.15)
                    waited += delay
                    time.sleep(delay)


class NakedClient:
    """The common starting point: call the API, and hand any error to the user."""

    def __init__(self, tts):
        self.tts = tts

    def request(self, text):
        try:
            self.tts.synth(text, model="flash")
            return {"ok": True, "attempts": 1, "waited": 0}
        except RuntimeError:
            return {"ok": False, "attempts": 1, "waited": 0}


def run_stress(client_kind: str, n: int = 10) -> dict:
    """Fire n concurrent requests (a simulated traffic spike) and report each outcome.

    The SafeClient gate is deliberately set to 4 while capacity is 3. That models the
    realistic case where you do not know the exact limit: the gate absorbs most of the
    overload, and the retry layer catches the few 429s that still get through. All
    three layers are visible in the result.
    """
    tts = make_tts()
    client = SafeClient(tts, max_concurrent=4) if client_kind == "safe" else NakedClient(tts)
    # Keep REAL-mode text extremely short so a stress run costs almost nothing.
    text = "Hi!" if not MOCK else "One user message that needs a spoken reply."
    results = [None] * n
    t0 = time.time()

    def fire(i):
        started = time.time()
        result = client.request(text)
        result["id"] = i + 1
        result["duration"] = round(time.time() - started, 2)
        results[i] = result

    threads = [threading.Thread(target=fire, args=(i,)) for i in range(n)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    failures = sum(1 for r in results if not r["ok"])
    retried = sum(1 for r in results if r["attempts"] > 1)
    return {"client": client_kind, "n": n, "results": results,
            "user_errors": failures, "retried": retried,
            "total_time": round(time.time() - t0, 2), "mock": MOCK}
