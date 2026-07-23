**English** | [繁體中文](README.zh-TW.md)

# Voice AI Pre-Sales & PoC Field Guide (for ElevenLabs Integration)

**How to run a discovery call for a voice AI project — and six runnable PoCs that answer
the questions the call raises.**

Most voice AI projects do not fail on the API. They fail because nobody asked about peak
concurrency, whose voice it is, or who owns the pronunciation dictionary — until after the
architecture was drawn.

This repository is two halves that depend on each other:

1. **[The interview guide](docs/presales-guide.md)** — what to ask a customer, per scenario,
   under four headings: Volume, Legal, Integration, Metrics. Plus the pitfall table: the
   failure modes we hit, their symptoms, and the fix.
2. **Six proofs of concept** — one per pattern, each can run with/without API key, so when a
   customer asks "can you show me?" you have something on screen in two minutes.

Written from a solutions engineer's point of view: ask the right questions first, then draw
the architecture.

## Start here

| If you are | Go to |
|---|---|
| Preparing for a discovery call | [docs/presales-guide.md](docs/presales-guide.md) |
| Deciding realtime vs batch, which product fits | [How to choose](#how-to-choose-an-approach) below |
| Deciding which voice, and whether you may clone it | [docs/voice-cloning.md](docs/voice-cloning.md) |
| Needing a demo on screen in two minutes | [Quick start](#quick-start) below |

```
elevenlabs-production-patterns/
├── docs/
│   ├── presales-guide.md  interview questions per scenario + the pitfall table
│   ├── voice-cloning.md   PVC / IVC / Voice Design decision guide
│   ├── diagrams/          architecture and decision diagrams
│   └── screenshots/       what each demo looks like running
├── 01-tts-cache/          publish-time generation + content-fingerprint cache
├── 02-stream-safeclient/  sentence streaming + concurrency gate and retry
├── 03-readalong-player/   STT alignment + stateless binary-search highlighting
├── 04-dubbing-workflow/   review state machine + optimistic lock + audit trail
├── 05-voice-agent/        Agents widget + webhook that verifies identity
└── 06-batch-registry/     voice registry + manifest-driven batch with retry
```

## Who this is for

Solutions engineers, solutions architects, and pre-sales technical staff who have to sit
across from a customer and scope a voice AI project — the point where "does the API work"
is already answered and the real questions are cost, latency, concurrency, review workflow,
and voice licensing.

It is also useful the other way round: if you are the customer, these are the questions a
good vendor should be asking you.

**Time to run:** any scenario, about two minutes, no API key, no account.

## Discovery in four questions

Ask in this order. Each one can disqualify the architecture you were about to draw.

| | Ask about | What the answer decides |
|---|---|---|
| **Volume** | Peak concurrency, monthly audio hours, growth | Plan, pricing, and whether you need a rate-limit strategy at all |
| **Legal** | Compliance regime, recording consent, whether the voice contract covers AI synthesis | Whether this can ship in the first place |
| **Integration** | Existing telephony, CRM and ERP reach, how user identity is carried | Most of the actual engineering effort |
| **Metrics** | Success criteria, and who owns prompts and dictionaries after launch | Acceptance, and whether it survives six months |

Per-scenario questions and the full pitfall table:
**[docs/presales-guide.md](docs/presales-guide.md)**.

## The six scenarios

Each one is the answer to a customer conversation that went a particular way.

| # | Scenario | The problem | The fix | [Article](https://medium.com/@mimichen123/six-production-patterns-for-voice-ai-and-the-questions-that-tell-you-which-one-you-need-6f6f43466c9c?sharedUserId=mimichen123) |
|---|----------|-------------|---------|------------|
| [01](01-tts-cache/) | Publisher article narration | Audio regenerated on every reader visit; the bill multiplies | Generate at publish time, cache on a content fingerprint | [Generate once, serve a million reads](https://medium.com/@mimichen123/generate-once-play-a-million-times-how-to-not-waste-your-tts-budget-3a58711b4e40?sharedUserId=mimichen123) |
| [02](02-stream-safeclient/) | Latency and rate limits | 4 seconds of silence before the first word; 429s at peak | Stream sentence by sentence; concurrency gate plus jittered backoff | [Rate-Limited TTS](https://medium.com/@mimichen123/stop-ddosing-yourself-a-three-layer-client-for-rate-limited-tts-apis-d0a8042b07bf?sharedUserId=mimichen123) / [TTFB 3.6s to 0.9s, no user-facing errors](https://medium.com/@mimichen123/from-4-1s-to-0-8s-cutting-voice-latency-with-sentence-streaming-681497d5d94e?sharedUserId=mimichen123) |
| [03](03-readalong-player/) | Read-along player | Highlighting drifts as soon as the user seeks | Align once offline; stateless binary search per tick | Correct at any playback position, O(log N) |
| [04](04-dubbing-workflow/) | Dubbing review board | Concurrent edits overwrite each other; approved lines get changed | State machine plus optimistic locking plus audit trail | Illegal moves refused, nothing silently lost |
| [05](05-voice-agent/) | E-commerce voice agent | The agent needs private order data it must not be trusted with | Webhook middleware that verifies identity server-side | Order lookup and human escalation, safely |
| [06](06-batch-registry/) | Game dialogue batch runs | One bad line kills a 300,000-line job | Voice registry plus a manifest-driven runner | Retry only what failed |

Ports match folder numbers: scenario `NN` runs on port `50NN`.

## Quick start

Every scenario is self-contained:

```bash
cd 01-tts-cache        # or any other scenario
pip install -r requirements.txt
python app.py          # scenario 01 -> http://localhost:5001
```

**MOCK mode is the default.** With no API key the scenario runs against a simulated
backend: zero cost, reproducible behaviour, and the full flow end to end. Learn the
shape of the problem here first.

**REAL mode** calls the actual API:

```bash
cp .env.example .env   # fill in ELEVEN_KEY, then restart
```

MOCK-mode numbers come from the simulated backend. They are deterministic and useful
for illustrating the shape of the fix, but they are not benchmarks of the ElevenLabs
API — run REAL mode for numbers from your own network and account.

## How to choose an approach

**Is a person waiting on the audio?**

- Yes, realtime: TTS `flash_v2_5` or `v3_conversational`, STT `scribe_v2_realtime`,
  and prefer small fast LLMs.
- No, batch: TTS `multilingual_v2` or `v3` for quality, STT `scribe_v2` batch (cheaper
  and more complete), with a queue to control concurrency and backoff for retries.

**What kind of problem is it?**

- A live conversation → ElevenLabs Agents (scenario 05)
- Producing content at volume → batch pipelines (scenarios 01 and 06)
- Understanding existing audio → Scribe (scenario 03)
- Which voice to use → [voice cloning decision guide](docs/voice-cloning.md)

## Diagrams

Hand-drawn architecture and pre-sales decision diagrams live in
[docs/diagrams/](docs/diagrams/), with an index of what each one covers.

> These diagrams are annotated in Traditional Chinese. They are linked rather than embedded
> so the English pages stay readable; the [繁體中文 README](README.zh-TW.md) and its
> per-scenario counterparts embed them inline. English versions are on the to-do list.

## What this is not

These are proofs of concept built to make one idea legible each. They have no
authentication, they store state in JSON files rather than a database, and they run on
Flask's development server. The patterns are meant to be lifted; the plumbing is not.

## License

[MIT](LICENSE)
