# Diagram index

> **Language note.** These diagrams are hand-drawn and annotated in Traditional Chinese.
> The English READMEs link to them rather than embedding them, so an English reader is not
> dropped into a wall of Chinese; the `README.zh-TW.md` files embed them inline. Redrawing
> them in English is an open task.

| File | What it shows | Used by |
|------|---------------|---------|
| `01-tts-cache-flow.png` | Publish-triggered generation and the content-fingerprint cache | scenario 01 |
| `02-streaming-latency.png` | Serial vs sentence-streaming timelines, and the SafeClient layers | scenario 02 |
| `03-readalong-sync.png` | Offline alignment, then stateless lookup at playback time | scenario 03 |
| `04-dubbing-review.png` | The review state machine and its refusal paths | scenario 04 |
| `05-voice-agent.png` | Agent, webhook middleware, and human escalation | scenario 05 |
| `06-batch-registry.png` | Voice registry, batch runner, manifest-driven retry | scenario 06 |
| `architecture-overview.png` | Repository layout (superseded by the tree in the root README) | — |
| `decision-tree-overview.png` | Realtime vs batch, and which product fits which problem | pre-sales guide |
| `how-to-ask-questions.png` | The Volume / Legal / Integration / Metrics interview flow | pre-sales guide |
| `voice-cloning-decision.png` | PVC vs IVC vs Voice Design | voice cloning guide |
| `agent-architecture.png` | Single-agent anatomy: prompt, tools, knowledge base | pre-sales guide |
| `multiagent.png` | When to split into sub-agents, and when not to | pre-sales guide |
| `RAG.png` | Knowledge base and retrieval design notes | pre-sales guide |
| `batch-pipeline.png` | Generic batch pipeline shape | scenarios 01, 06 |
| `dubbing.png` | Dubbing pipeline overview | scenario 04 |
| `meeting-transcription.png` | Meeting transcription reference architecture | pre-sales guide |
| `web-app-assistant.png` | In-app voice assistant reference architecture | pre-sales guide |
| `cheatsheet.png` | One-page model and product cheat sheet | pre-sales guide |

## Screenshots

Live UI captures live in [`docs/screenshots/`](../screenshots/) and are embedded at the top
of each scenario README:

| File | Shows |
|------|-------|
| `5001.png` | Audio admin console, MOCK mode, three articles ready |
| `5002.png` | Latency lab: TTFB 3.60s to 0.89s, plus the 429 chip wall |
| `5003.png` | Read-along upload page in MOCK mode |
| `5004.png` | Review board with an "edited after approval" line |
| `5005.png` | Storefront with no agent configured (setup instructions) |
| `5005-widget.png` | The Agents widget once ELEVEN_AGENT_ID is set |
| `5006.png` | Batch console: nine lines ok, L009 failed, retry button armed |

## Known gaps

1. **Annotations are in Chinese.** Redrawing the six scenario diagrams with English labels
   would let the English READMEs embed them directly. The Excalidraw source is the place
   to start.
2. **Embedded UI captures are stale.** Several diagrams contain screenshots of the demo UI
   from before it was translated, so they still show the old Chinese interface. The current
   English captures are in [`docs/screenshots/`](../screenshots/) and can be dropped in.
