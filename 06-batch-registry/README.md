**English** | [繁體中文](README.zh-TW.md)

# Game Localization Batch Console — "Patch 1.4" (Scenario 6)

Customer scenario: a game studio generates voice lines for multiple characters across multiple languages (English and Spanish in this demo). At 10 lines it's cute; at 300,000 lines, three things decide whether you survive the month:

1. **Voices are assets** — `REGISTRY: (character, language) -> voice_id` lives in a lookup table (fed by env vars), not scattered through code. Swapping a licensed voice = changing one entry.
2. **One failed line must not kill the batch** — a missing voice mapping or API failure is recorded in the manifest and the batch moves on. The CSV deliberately contains a "ghost" character with no registry entry to prove the guardrail (L009 always fails).
3. **Batches protect themselves** — reuses Scenario 2's SafeClient (semaphore + queue + backoff/jitter); batch jobs are the easiest way to DDoS your own quota.

The manifest (`data/manifest.json`) records per line: status ok/failed, voice_id used, retry count, characters consumed. That enables the money button: **"retry failed only"** (`run_batch(only_ids=failed)`) — at 300k-line scale, re-running everything vs. re-running 47 failures is a monthly-bill-sized difference.

![Batch console](../docs/screenshots/5006.png)

*Nine lines succeed, L009 fails with `no voice mapping in REGISTRY`, and the batch finishes anyway. "Retry failures only (1)" re-runs exactly that line.*

## Quick Start

```bash
pip install -r requirements.txt
python app.py
# open http://localhost:5006/
```

**MOCK mode (default)**: each voice_id gets a distinct pitch so you can *hear* "different characters, different voices" at zero cost.
**REAL mode**: `cp .env.example .env`, fill `ELEVEN_KEY` + pick commercially-licensed voices from the Voice Library and set `VOICE_HERO_EN` / `VOICE_HERO_ES` / `VOICE_MERCHANT_EN` / `VOICE_MERCHANT_ES`.

Try it: "Run batch" -> 9/10 ok, L009 fails (no voice mapping) -> "Retry failed only" re-runs exactly that one. Run batch twice -> everything already ok is skipped (manifest-driven idempotency).

## Pre-sales questions

1. How big is the character x language matrix? Are all voices commercially licensed?
2. What's the line count? (10 lines and 300k lines are different worlds)
3. Who maintains the pronunciation dictionary for game jargon?

## File Guide

| File | Role |
|------|------|
| `engine.py` | REGISTRY, MockTTS/RealTTS, SafeClient, manifest-driven run_batch |
| `app.py` | Flask: console page + run/retry_failed APIs |
| `data/lines.csv` | Dialogue source (includes the deliberate ghost-character trap) |
| `data/manifest.json` | Per-line status/voice/retries/chars — the console's data source |

## Architecture diagram

A hand-drawn diagram covering the registry, batch runner and retry loop is available at
[`docs/diagrams/06-batch-registry.png`](../docs/diagrams/06-batch-registry.png).

> Note: the diagram is annotated in Traditional Chinese. It is linked rather than embedded
> here so this page stays readable in English; the [繁體中文 README](README.zh-TW.md)
> embeds it inline.
