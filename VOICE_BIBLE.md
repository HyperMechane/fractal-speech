# HyperMechane Voice Bible (v1)

> **Calm. Precise. Intelligent. Human.**
> Build. Measure. Evolve.

Reference persona: *an experienced engineer explaining something important to another intelligent person.*
Never: *"Welcome guys! Today we're SUPER EXCITED to show you..."*

Applies to: BUILDING HYPERMECHANE, HYPERMECHANE LAB, ENGINEERING NOTES, PRODUCT DEMOS.

## The standard

| Aspect | Standard |
|---|---|
| Language | English, international / neutral |
| Accent | Light, neutral American English |
| Voice | Male, apparent age 35-45 |
| Timbre | Medium-low, clean, warm |
| Personality | Intelligent, calm, precise, confident |
| Pace | Moderate, about 145-155 words/minute |
| Energy | Low-moderate, rising only at important moments |
| Emotion | Restrained: conviction without drama |
| Diction | Extremely clear, especially technical terms |
| Pauses | Natural between ideas; slightly longer before key concepts |
| Style | Documentary / technical storytelling |
| Avoid | Commercial voice, artificial enthusiasm, "startup bro", trailer announcer, excess drama |

## Consistency rules (same on video 1 and video 50)

1. Same voice, same speed, same pause logic: all of it lives in `voice_profile.json`. Do not override it with CLI flags for published videos.
2. Same pronunciation of HyperMechane: `pronunciations.json`.
3. Same narrative stance: calm, direct, no hype. Write scripts in short, declarative sentences.
4. Use `[beat]` before a key concept; use `[pause N]` only for scene changes.
5. After each render, check the `Pace:` line. If it is outside 145-155 words/min, adjust `speed` in the profile (not per video) and re-render.

## What is enforced in code, and what is not

- Enforced: voice, speed, pause lengths, `[beat]`, pronunciation dictionary, pace report.
- By ear only: "35-45 years", "warm", "calm", "confident". Kokoro has no controls for these; the voice choice (`am_adam`, `am_michael`, `am_fenrir`) is the only lever. Compare with `--compare-voices` and record the decision here.

## Change log

- v1: standard defined. Voice: `am_adam` (to be confirmed by ear against `am_michael` and `am_fenrir`).
