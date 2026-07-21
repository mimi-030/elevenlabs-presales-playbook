**English** | [繁體中文](README.zh-TW.md)

# Read-Along Classroom — word-level sync player (Scenario 3)

Customer scenario: a language-learning product wants karaoke-style read-along — the word being spoken lights up, clicking any word seeks the audio. Upload a recording, get a player.

Two design decisions this PoC proves:

1. **Alignment happens once, offline** — STT (Scribe, with diarization) produces word-level timestamps stored as static JSON. The player never calls an API.
2. **Playback lookup is stateless** — every 100ms the frontend runs `findActive(words, audio.currentTime)`: a **binary search O(log N)** over the sorted word array. No cursors, no state to corrupt: scrub, jump, rewind, or speed-change the progress bar however you like — it re-locates instantly.

Edge cases handled (deliberately visible in the demo):
- silence between sentences -> nothing highlights (End Check: `t <= words[ans].end`)
- time outside the transcript range -> stateless zero, no crash (boundary check O(1))
- reverse lookup: click any `<span>` -> `audio.currentTime = words[i].start`

![Upload page](../docs/screenshots/5003.png)

*MOCK mode asks for the transcript alongside the recording, then lays the words across the real duration — enough to exercise the whole sync UI without an API key.*

## Quick Start

```bash
pip install -r requirements.txt
python app.py
# open http://localhost:5003/  -> upload a recording
```

**MOCK mode (default, no API key)**: paste the transcript along with your audio; words are distributed over the audio duration (with sentence-end pauses) — test the whole sync UI at zero cost.

**REAL mode**: `cp .env.example .env`, fill in `ELEVEN_KEY` -> uploads go to ElevenLabs STT (Scribe) for true word-level timestamps + speaker diarization.

## Architecture

```
UPLOAD SIDE                                    PLAYER SIDE
POST /api/transcribe                           GET /player/<pid>
  save audio -> mock/real STT                    loads static JSON config
  -> data/projects/<pid>.json                    per 100ms: binary search findActive()
  { audio_url, words[] }                         hit -> highlight span; click span -> seek
```

## Pre-sales questions

1. Do you really need realtime transcription? (~80% of use cases don't — batch is cheaper and richer)
2. What's the audio source and quality? One speaker or many? (get the hardest sample and test diarization)
3. Recording compliance: consent notice, retention period, zero-retention requirements?

## File Guide

| File | Role |
|------|------|
| `stt.py` | Transcription layer: mock/real behind one interface -> words[] with timestamps |
| `sync_logic.py` | The binary search + boundary/end checks (pure logic, unit-testable) |
| `app.py` | Flask: upload page, transcribe API, player page |
| `templates/` | upload / player pages |

## Architecture diagram

A hand-drawn diagram covering offline alignment and the playback-time lookup is available at
[`docs/diagrams/03-readalong-sync.png`](../docs/diagrams/03-readalong-sync.png).

> Note: the diagram is annotated in Traditional Chinese. It is linked rather than embedded
> here so this page stays readable in English; the [繁體中文 README](README.zh-TW.md)
> embeds it inline.
