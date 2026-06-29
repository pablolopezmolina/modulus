# MODULUS Wearable — Garmin Health Analytics

Personal health-analytics layer that ingests sensor data from a **Garmin
Fenix 5 Plus** (and compatible devices) and computes **recovery, sleep,
readiness, cardio-fitness and longevity** scores, enriched with **manual
self-reported inputs**.

> **Honest framing.** The scoring algorithms of WHOOP, Oura and Apple Watch are
> proprietary and unpublished — they **cannot be reproduced exactly** from the
> outside. This module instead implements **transparent, peer-reviewed-physiology
> based approximations** that target the *same constructs* (overnight
> HRV-driven recovery, sleep-stage sleep quality, Oura-style readiness,
> Apple-style cardio fitness). Every formula is documented and every weight is
> tunable, so you can calibrate the output toward whichever device you trust.

---

## Data flow

```
Garmin Fenix 5 Plus
        │  records FIT files (sleep, monitoring, HRV status, VO2max)
        ▼
 .FIT files  ──►  FitFileSource (garmin-fit-sdk)  ─┐
 (offline,        build_records() aggregation       │
  no creds)                                          ▼
 SyntheticSource (tests/demo) ─────────────────►  DailyRecord(s)  +  manual inputs
                                                     │
                                                     ▼
                              Personal Baseline (trailing 30–60 days)
                                                     │
        ┌───────────────┬───────────────┬───────────┴───────┬──────────────┐
        ▼               ▼               ▼                   ▼              ▼
     sleep          recovery        readiness          cardio_fitness   longevity
   (Oura/WHOOP)     (WHOOP)          (Oura)             (Apple)          (composite)
```

## Getting your data off the watch (no credentials)

The primary path is **FIT files**, which work fully offline:

1. **Garmin Connect → Export Original** for an activity/day, *or*
2. Connect the Fenix over USB and copy `GARMIN/Monitor/*.FIT` (daily wellness +
   sleep) and `GARMIN/Activity/*.FIT`.

Then point the parser at them:

```python
from src.wearable.ingestion import FitFileSource
source = FitFileSource.from_directory("/path/to/fit/files")
records = source.records()          # -> list[DailyRecord]
```

`garmin-fit-sdk` is the official, pure-Python decoder (in `requirements.txt`).
If it is not installed, `FIT_AVAILABLE` is `False` and the rest of the stack
still works on synthetic or pre-decoded data.

## Scores & scientific basis

| Score | Mirrors | Key inputs | Anchored on |
|-------|---------|------------|-------------|
| **Sleep** | Oura / WHOOP | duration vs need, efficiency, REM %, deep %, latency, awakenings | Hirshkowitz 2015; Ohayon 2004 |
| **Recovery** | WHOOP | overnight HRV (rMSSD) vs baseline, resting HR, sleep, respiration | Plews 2013 (HRV & readiness) |
| **Readiness** | Oura | previous sleep, HRV balance, resting HR, body-temp deviation, subjective wake fatigue | Oura contributor model |
| **Cardio fitness** | Apple Watch | VO2max (device or Uth–Sørensen estimate), age/sex norms, fitness age | Uth 2004; Cooper Institute norms |
| **Longevity** | — (composite) | VO2max, steps, sleep duration + regularity, resting HR, HRV | Mandsager 2018; Paluch 2022; Windred 2023; Zhang 2016; Jarczok 2022 |

All scores are scored against a **personal rolling baseline** where applicable —
a HRV of 55 ms is only "good" relative to *your* normal. Without enough history,
fixed physiological anchors are used so a number is always returned.

## Manual inputs

The watch only sees physiology. The app accepts the behavioural / subjective
signals you asked for, all sharing a common envelope (`src/wearable/manual.py`):

- **Bowel movements** — count + Bristol stool scale.
- **Supplements** — compound, dose, unit, route, timing.
- **Peptides** — name, dose, unit, route, timing.
- **Emotional state** — valence/arousal (Russell circumplex) or a label.
- **Fatigue on waking / before sleep** — 1–10.
- **Post-meal nap desire** — 0–10.

Subjective wake fatigue feeds the readiness score; the rest are stored for trend
correlation and future modelling.

## REST API

```bash
uvicorn src.wearable.api:app --reload --port 8010
# docs at http://localhost:8010/docs
```

Endpoints: `/profile`, `/ingest/fit`, `/ingest/synthetic`, `/records`,
`/manual/{day}`, `/scores/{day}`, `/longevity`, `/dashboard`.

## Try it offline

```bash
python scripts/demo_wearable.py
```

Generates 45 days of synthetic data and prints a full score breakdown.

## Limitations

- **Not a medical device.** Scores are for personal tracking, not diagnosis.
- FIT field names vary across firmware; the parser is defensive and tolerates
  missing fields, but mappings may need tuning for a specific export.
- The longevity index is a **heuristic composite**, not a validated clinical
  predictor.
- Exact parity with WHOOP/Oura/Apple is impossible; calibrate the (exposed)
  weights against your own device readings if you want closer alignment.
```
