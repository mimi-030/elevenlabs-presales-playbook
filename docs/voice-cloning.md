**English** | [繁體中文](voice-cloning.zh-TW.md)

# Voice Cloning Decision Guide

```
Do you need a specific real person's voice?
├─ NO  -> Voice Design or Voice Library (fastest; first choice for PoCs)
└─ YES -> Quality bar?
    ├─ High            -> PVC (Professional Voice Cloning): 30 min recording, 3-6 hr queue+training
    └─ Low / quick test -> IVC (Instant Voice Cloning): 1-5 min recording
```

## Ask legal before touching anything

1. **Does the spokesperson's voice contract cover AI synthesis? For how long?**
   Getting halted by legal after launch is a real story — ask about the licensing chain during discovery.
2. **Do you need brand voice alignment?**
   One voice_id across call agents, ads, and the app keeps the brand voice consistent.

## Practical advice

- During PoC, always use Voice Library (commercially licensed) or Voice Design — don't wait for PVC training
- Pin voice_id and seed for reproducible output (scenario 6's registry exists for this)
- Voices with expiring licenses need a takedown-and-replace path (the registry makes it a one-entry swap)
