"""
engine.py - scenario 4: the dubbing review state machine.

Five mechanisms, each answering a real complaint from a dubbing team:

  1. Rule table (state, action, role) -> next_state. The workflow is data, not a pile
     of if-statements, and any move that is not in the table is rejected.
  2. Editing an APPROVED line automatically sends it back for review and flags it.
     This is the fix for the classic incident: a line is approved, someone tweaks it,
     and the unreviewed version ships.
  3. Optimistic locking on version. Two people editing the same line at once means the
     second one is told, not silently overwritten.
  4. An append-only transition log: who did what, from which state to which, and when.
     This is what the History panel reads.
  5. A REGENERATING state. Audio generation takes minutes, so the line is visibly busy
     and the approve action is unreachable while it is - which stops anyone approving
     a line while listening to the previous take.
"""
import os, json, time, wave, math, struct, threading
from enum import Enum

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
BASE = os.path.dirname(__file__)
AUDIO_DIR = os.path.join(BASE, "static", "audio")
STORE = os.path.join(BASE, "data", "store.json")
_lock = threading.Lock()


class S(str, Enum):
    DRAFT = "draft"
    REGEN = "regenerating"            # 5. audio is being generated (a minutes-long task)
    REVIEW = "in_review"
    FIX = "changes_requested"
    OK = "approved"


# ---------- 1. the rule table: the whole workflow on one screen ----------
RULES = {
    (S.DRAFT,  "edit",        "translator"): S.DRAFT,
    (S.DRAFT,  "submit",      "translator"): S.REGEN,
    (S.REGEN,  "audio_ready", "system"):     S.REVIEW,   # system event: audio landed
    (S.REVIEW, "approve",     "reviewer"):   S.OK,
    (S.REVIEW, "reject",      "reviewer"):   S.FIX,
    (S.FIX,    "edit",        "translator"): S.FIX,
    (S.FIX,    "submit",      "translator"): S.REGEN,
    (S.OK,     "edit",        "translator"): S.REGEN,    # 2. edited after approval -> re-review
}
# Anything not in the table is refused: approving while regenerating, editing a line
# that is out for review, a translator approving their own work, and so on.


class ConflictError(Exception):
    """Optimistic lock failure: the caller is holding a stale version."""


class ForbiddenError(Exception):
    """The rule table has no entry for this (state, action, role)."""


# ---------- storage (a JSON file standing in for a database) ----------
def _load():
    with open(STORE, encoding="utf-8") as f:
        return json.load(f)


def _save(db):
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)


def all_lines():
    db = _load()
    return sorted(db["lines"].values(), key=lambda x: x["order"])


# ---------- audio layer (mock: a short tone per version / real: TTS) ----------
def _mock_audio(line_id, text, version):
    path = os.path.join(AUDIO_DIR, f"{line_id}_v{version}.wav")
    rate, seconds = 22050, min(0.8 + len(text) * 0.06, 4.0)
    # Pitch is derived from text and version, so editing a line audibly produces a
    # different take. Reviewers can hear that they are listening to something new.
    freq = 240 + (hash((text, version)) % 320)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        n = int(rate * seconds)
        w.writeframes(b"".join(
            struct.pack("<h", int(10000 * min(1, i / 1500, (n - i) / 1500)
                                  * math.sin(2 * math.pi * freq * i / rate)))
            for i in range(n)))
    return f"{line_id}_v{version}.wav"


def _real_audio(line_id, text, version):
    import requests
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128",
        json={"text": text,
              "model_id": os.environ.get("ELEVEN_MODEL", "eleven_multilingual_v2")},
        headers={"xi-api-key": API_KEY}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"TTS {r.status_code}")
    filename = f"{line_id}_v{version}.mp3"
    with open(os.path.join(AUDIO_DIR, filename), "wb") as f:
        f.write(r.content)
    return filename


def _generate_async(line_id):
    """5. Generate in the background, then let the system fire audio_ready.

    While this runs the line stays in REGENERATING, and because the rule table has no
    (REGEN, approve, reviewer) entry, the approve action is locked out for free.
    """
    def job():
        with _lock:
            db = _load()
            line = db["lines"][line_id]
            text, version = line["text"], line["version"]
        if MOCK:
            time.sleep(2.0)                            # long enough to see the state in the UI
            filename = _mock_audio(line_id, text, version)
        else:
            filename = _real_audio(line_id, text, version)
        apply_action(line_id, "audio_ready", actor="platform", role="system",
                     _audio_file=filename)

    threading.Thread(target=job, daemon=True).start()


# ---------- the single door every action goes through ----------
def apply_action(line_id, action, actor, role,
                 new_text=None, expected_version=None, comment=None, _audio_file=None):
    with _lock:
        db = _load()
        line = db["lines"].get(line_id)
        if not line:
            raise KeyError("no such line")
        current = S(line["status"])

        # 3. Optimistic lock: an edit must state which version the editor was looking at.
        if action == "edit":
            if expected_version is None or int(expected_version) != line["version"]:
                raise ConflictError(
                    f"This line has already moved to v{line['version']} - "
                    f"you are editing an older version. Reload and try again.")

        key = (current, action, role)
        if key not in RULES:                           # 1. not on the rails, refuse
            raise ForbiddenError(f"a {role} cannot '{action}' a line that is '{current.value}'")

        previous = current
        line["status"] = RULES[key].value

        if action == "edit" and new_text is not None:
            line["text"] = new_text
            line["version"] += 1
            if previous == S.OK:                       # 2. edited after approval: flag it
                line["changed_after_approval"] = True
        if action == "approve":
            line["changed_after_approval"] = False
        if _audio_file:
            line["file"] = _audio_file

        line["transitions"].append({                   # 4. append-only audit log
            "action": action, "actor": actor, "role": role,
            "from": previous.value, "to": line["status"],
            "comment": comment, "at": time.strftime("%m/%d %H:%M:%S")})
        db["lines"][line_id] = line
        _save(db)
        result = dict(line)

    # Both submit and edit-after-approval land in REGENERATING, which kicks off audio.
    if RULES[key] == S.REGEN:
        _generate_async(line_id)
    return result


# ---------- seed data, so the board has a story to tell on first run ----------
def seed_if_empty():
    if os.path.exists(STORE):
        return

    def make(line_id, order, character, source, text, status,
             version=0, changed_after_approval=False, transitions=None, file=None):
        return {"id": line_id, "order": order, "character": character, "source": source,
                "text": text, "status": status, "version": version,
                "changed_after_approval": changed_after_approval, "file": file,
                "transitions": transitions or []}

    def step(action, actor, role, from_state, to_state, at, comment=None):
        return {"action": action, "actor": actor, "role": role,
                "from": from_state, "to": to_state, "comment": comment, "at": at}

    lines = {}

    # L212 - the happy path: submitted, generated, approved.
    f = _mock_audio("L212", "That was our last chance.", 0)
    lines["L212"] = make("L212", 1, "Rin", "그게 마지막 기회였어", "That was our last chance.",
        S.OK.value, file=f, transitions=[
            step("submit", "amy", "translator", "draft", "regenerating", "07/10 09:12"),
            step("audio_ready", "platform", "system", "regenerating", "in_review", "07/10 09:13"),
            step("approve", "bob", "reviewer", "in_review", "approved", "07/10 11:30")])

    # L213 - waiting for a reviewer.
    f = _mock_audio("L213", "So then... what do we do now?", 0)
    lines["L213"] = make("L213", 2, "Rin", "그래서... 이제 어떡해", "So then... what do we do now?",
        S.REVIEW.value, file=f, transitions=[
            step("submit", "amy", "translator", "draft", "regenerating", "07/10 13:40"),
            step("audio_ready", "platform", "system", "regenerating", "in_review", "07/10 13:41")])

    # L214 - rejected, with the reviewer's note attached.
    f = _mock_audio("L214", "Get out of my way!", 0)
    lines["L214"] = make("L214", 3, "Gus", "비켜!", "Get out of my way!",
        S.FIX.value, file=f, transitions=[
            step("submit", "amy", "translator", "draft", "regenerating", "07/10 14:02"),
            step("audio_ready", "platform", "system", "regenerating", "in_review", "07/10 14:03"),
            step("reject", "bob", "reviewer", "in_review", "changes_requested", "07/10 15:20",
                 "Too aggressive. This character is gruff on the surface, soft underneath.")])

    # L215 - the incident, replayed: approved, then edited. The system catches it with
    # a flag and an automatic trip back through review.
    f = _mock_audio("L215", "I'll never forget you.", 1)
    lines["L215"] = make("L215", 4, "Rin", "널 잊지 않을게", "I'll never forget you.",
        S.REVIEW.value, version=1, changed_after_approval=True, file=f, transitions=[
            step("submit", "amy", "translator", "draft", "regenerating", "07/09 16:00"),
            step("audio_ready", "platform", "system", "regenerating", "in_review", "07/09 16:01"),
            step("approve", "bob", "reviewer", "in_review", "approved", "07/09 17:45"),
            step("edit", "amy", "translator", "approved", "regenerating", "07/10 14:02",
                 "Tone tweak: never forget -> won't forget? (saved a draft by mistake)"),
            step("audio_ready", "platform", "system", "regenerating", "in_review", "07/10 14:02")])

    # L216 - still a draft, the translator is working on it.
    lines["L216"] = make("L216", 5, "Gus", "다들 도망쳐!", "Everyone, run!", S.DRAFT.value)

    _save({"lines": lines})
