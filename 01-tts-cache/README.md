**English** | [繁體中文](README.zh-TW.md)

# Publisher TTS Pipeline — "Meridian Financial" (Scenario 1)
**Read the Case Study:** [Generate Once, Play a Million Times: How to Not Waste Your TTS Budget](https://medium.com/@mimichen123/generate-once-play-a-million-times-how-to-not-waste-your-tts-budget-3a58711b4e40)

Simulates a publisher's full article-to-audio flow: a **reader-facing article page** (instant playback of pre-generated audio) plus an **editor-facing audio admin panel** (generate / cache / retry failures / cost tracking).

Customer pain point: if audio generation is triggered by *reader visits*, the same article gets generated thousands of times (the classic 20x bill incident). This PoC proves the correct architecture: **generate once at publish time -> store -> every reader plays the same file**.

![Audio admin console](../docs/screenshots/5001.png)

*The editor-side console in MOCK mode. Click "Generate all" twice and the last-action column turns to `skipped (unchanged)` — that is the content-fingerprint cache, at zero cost.*

## Quick Start

```bash
pip install -r requirements.txt
python app.py
# Reader side  http://localhost:5001/
# Editor side  http://localhost:5001/admin
```

**MOCK mode by default** (no API key): generates a placeholder WAV so you can walk the whole flow at zero cost — get familiar with the UI and cache behavior here first.

**REAL mode** (actually calls ElevenLabs):

```bash
cp .env.example .env    # fill in ELEVEN_KEY — never hardcode or commit it
python app.py
```

## Suggested Test Sequence (each step proves one design decision)

1. Open the admin panel -> click "Generate all" -> three articles turn "generated"
2. **Click "Generate all" again** -> the "last action" column shows `skipped (unchanged)` everywhere — that's the content-fingerprint cache, costing nothing
3. Open any article on the reader side -> the player starts instantly (readers only ever get pre-built files)
4. Edit any article body in `data/articles.json` -> back to admin, click "Generate" -> only that article regenerates
5. In REAL mode: listen to a001 — "(2330)" is read digit by digit as a ticker, "15%" becomes "15 percent" and "$34B" becomes "34 billion dollars", all courtesy of `normalize()` (financial copy cannot be fed to TTS raw)

## Architecture

```
[Editor edits articles.json / clicks generate]      Reader side
        | on_publish()                                | GET /article/<id>
        v                                             v
  normalize() financial-text preprocessing      reads manifest + plays stored file
        |                                       (zero API calls, zero cost)
  content_hash compare --unchanged--> skip
        | changed
  MOCK: placeholder WAV / REAL: ElevenLabs TTS (retry + backoff built in)
        |
  save to static/audio/ + record status/chars/errors in data/manifest.json
```

## File Guide

| File | Role |
|------|------|
| `tts_pipeline.py` | Core pipeline: normalize, cache, dual-mode generation, retry, manifest |
| `app.py` | Flask routes: 2 reader pages + 1 admin page + 3 APIs |
| `data/articles.json` | Sample articles (bodies deliberately contain tickers and % to exercise normalize) |
| `data/manifest.json` | Audio state store (auto-generated; the admin panel's data source) |
| `templates/` | home / article / admin pages |

## Productise note

The "publish-triggered + content-fingerprint cache + observable failures" pattern holds for every media customer — it could ship as a publisher helper in the official SDK or as a reference doc, so customers stop reinventing it.

## Architecture diagram

A hand-drawn diagram covering the publish-time generation and cache flow is available at
[`docs/diagrams/01-tts-cache-flow.png`](../docs/diagrams/01-tts-cache-flow.png).

> Note: the diagram is annotated in Traditional Chinese. It is linked rather than embedded
> here so this page stays readable in English; the [繁體中文 README](README.zh-TW.md)
> embeds it inline.
