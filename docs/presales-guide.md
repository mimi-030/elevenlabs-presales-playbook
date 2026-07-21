**English** | [繁體中文](presales-guide.zh-TW.md)

# Pre-sales Interview Guide (Solutions Engineer's view)

## Mnemonic: Volume / Legal / Integration / Metrics

| Aspect | What to ask | What it decides |
|---|---|---|
| **Volume** | Peak concurrency? Monthly audio hours? Growth? | Plan & pricing, rate-limit design |
| **Legal** | HIPAA/GDPR? Recording consent? Does the voice contract cover AI synthesis? | Whether the architecture can ship at all |
| **Integration** | Existing telephony (Twilio/SIP)? How to reach CRM/ERP? How is user identity carried? | Integration effort |
| **Metrics** | Success criteria (containment rate / TTFB / cost)? Who owns prompts and dictionaries? | Acceptance & long-term operations |

## Per-scenario interview questions

### 01 Article narration / batch content
1. Monthly audio hours? Growth? -> decides plan and price
2. Domain terms that must be pronounced correctly? Who maintains the dictionary?
3. Manual or automatic QC? -> different pipelines
4. Publishing where? If it's just narrating articles on your own site, one Audio Native embed solves it — don't build the whole pipeline

### 02 Realtime streaming
1. Acceptable time-to-first-byte (TTFB) target?
2. Peak concurrency? -> semaphore capacity vs. plan limits

### 03 Transcription / read-along
1. Do you really need realtime transcription? -> ~80% don't
2. Audio source quality? One speaker or many? -> test diarization on the hardest sample
3. Recording compliance: consent, retention period, zero retention needed?

### 04 Dubbing / localization
1. Target languages and quality bar?
2. Script already available? -> skip STT, better quality
3. Human-in-the-loop or fully automatic? -> very different cost
4. Original speaker's voice licensing settled?

### 05 Voice agent
1. Current phone system? -> Twilio integration or SIP trunk
2. Peak simultaneous calls?
3. Which situations must transfer to a human? To which number?
4. What may/may not be discussed? (guardrail scope)
5. If the customer brings their own LLM, agree upfront who owns latency and hallucination

### 06 Multi-character batch
1. How big is the character x language matrix? All voices commercially licensed via Voice Library?
2. Line count? (10 lines and 300k lines are different worlds)

## Pitfall table

| Pitfall | Symptom | Fix |
|---|---|---|
| 429 rate limit | Batch jobs fail en masse | Exponential backoff + queue-controlled concurrency + log xi-request-id |
| Old models | scribe_v1 calls fail | Removed 2026/7 — migrate to scribe_v2 |
| Frontend trust | Users forge overrides to escalate privileges | Every backend tool verifies independently; agent trust_context = low |
| Slow tools | Awkward silence mid-conversation | Pre-tool speech + soft-timeout filler |
| Hallucinated prices/policy | Agent says things not in the KB | Prompt-mandated refusals + source_attribution + eval regression suite |
| Cost explosion | Credits gone before month end | Budget x1.75, monitor overage, cheaper models per scenario |
| Voice licensing | Legal halts launch after go-live | Ask about the licensing chain during discovery; use Library/Design voices for PoC |
| No test set | Every prompt change is judged by feel | Use the platform's built-in Tests/Evals; every change runs regression |

## RAG knowledge base notes
- Where is the KB now? How often updated? By whom? Every document needs an owner and update cadence (that's how agents end up quoting old prices)
- Large KB -> RAG; keep the system prompt under ~a thousand words
- The platform's built-in KB removes the external embedding pipeline — unless the customer already has a mature one
- Retrieval failures are usually document-quality problems, not LLM problems
- Different customers get different offers? -> tools + authenticated queries, not the KB

## Multi-agent splitting principles
- Longer prompts = worse adherence, higher latency, harder testing -> split into sub-agents: short prompt, few tools, small KB, predictable behavior
- But **only split when toolsets or knowledge bases clearly differ** — don't split for its own sake
- The router agent only classifies intent; when unsure, it asks
- Each node can override voice/LLM/tools independently; every node's prompt needs an owner
