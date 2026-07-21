"""
stt.py - the transcription layer (mock and real share one interface).

REAL: upload the audio file to ElevenLabs STT (Scribe) and get word-level timestamps.
MOCK: you record yourself and paste your own transcript. The words are laid out across
      the real duration of the file, with longer gaps after sentence endings. That is
      enough to exercise the whole sync UI at zero cost.

Both modes return the same shape: words = [{text, start, end, speaker}]
"""
import os, re

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
MOCK = API_KEY is None
PUNCTUATION = ",.!?;: \n" + "，。！？、；："
SENTENCE_END = ".!?" + "。！？"


def _tokenize(text: str):
    """Split into display tokens: whole words for Latin script, single characters for
    CJK. Punctuation attaches to the token before it, because that is how it is read.

    Both scripts are handled so the same player works for an English lesson and a
    Chinese one.
    """
    tokens, buffer = [], ""
    for char in text:
        if re.match(r"[a-zA-Z0-9']", char):
            buffer += char                          # Latin/digits: accumulate into a word
        else:
            if buffer:
                tokens.append(buffer)
                buffer = ""
            if char in PUNCTUATION:
                if char.strip() and tokens:         # attach punctuation to the previous token
                    tokens[-1] += char
            else:
                tokens.append(char)                 # CJK: one character per token
    if buffer:
        tokens.append(buffer)
    return tokens


def mock_transcribe(text: str, duration: float) -> list:
    """Lay the transcript across the recording.

    Time is allocated by token length, and sentence endings get a noticeably longer
    pause. Those pauses create real silent gaps, which is exactly the edge case the
    player has to get right (do not highlight anything during silence).
    """
    tokens = _tokenize(text)
    if not tokens:
        return []
    weights = [max(len(t.rstrip(PUNCTUATION)), 1) for t in tokens]
    pause_after = [0.45 if t and t[-1] in SENTENCE_END else 0.06 for t in tokens]
    speech_total = max(duration - sum(pause_after), duration * 0.6)
    unit = speech_total / sum(weights)

    words, cursor, speaker = [], 0.15, "A"
    for token, weight, pause in zip(tokens, weights, pause_after):
        start = round(cursor, 2)
        end = round(cursor + weight * unit, 2)
        words.append({"text": token, "start": start, "end": end, "speaker": speaker})
        cursor = end + pause
        if token and token[-1] in SENTENCE_END:
            speaker = "B" if speaker == "A" else "A"   # alternate speakers so the filter is demoable
    return words


def real_transcribe(audio_path: str) -> list:
    """Call the STT API: multipart upload, asking for word timestamps and diarization."""
    import requests
    with open(audio_path, "rb") as f:
        r = requests.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": API_KEY},
            data={"model_id": "scribe_v1", "diarize": "true",
                  "timestamps_granularity": "word"},
            files={"file": (os.path.basename(audio_path), f)},
            timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"STT API {r.status_code}: {r.text[:200]}")
    words = []
    for word in r.json().get("words", []):
        if word.get("type") == "spacing":          # spacing tokens are the silence; skip them
            continue
        words.append({"text": word["text"], "start": round(word["start"], 2),
                      "end": round(word["end"], 2),
                      "speaker": word.get("speaker_id", "A")})
    return words
