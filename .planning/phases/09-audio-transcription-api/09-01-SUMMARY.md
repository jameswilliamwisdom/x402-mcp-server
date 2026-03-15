---
phase: 09-audio-transcription-api
plan: "01"
subsystem: api
tags: [faster-whisper, fastapi, fastapi-x402, httpx, pyav, ssrf, transcription, x402, whisper, slowapi]

# Dependency graph
requires:
  - phase: 05-web-scraping-api
    provides: SSRFMiddleware pattern, validate_url_for_ssrf(), LIFO middleware ordering
  - phase: 06-file-conversion-api
    provides: httpx streaming download with chunk accumulator, redirect SSRF hook pattern
  - phase: 07-web-search-api
    provides: decoded_payment["payload"]["authorization"]["from"] wallet extraction
  - phase: 08-email-sending-api
    provides: fastapi-x402 init_x402 + @pay pattern, threading.Lock rate limit pattern
provides:
  - FastAPI transcription service with faster-whisper small/int8/CPU
  - x402 payment gate at $0.05 per transcription
  - SSRF-protected audio download with 25MB streaming size cap
  - PyAV duration check (no system ffmpeg required)
  - Auto language detection with language_probability in response
  - Optional word-level timestamps via word_timestamps parameter
  - Free GET /transcribe/test fixture endpoint (100/hour rate limit)
affects: [10-mcp-server-update, deployment, home-server-setup]

# Tech tracking
tech-stack:
  added:
    - faster-whisper>=1.2.1 (CTranslate2 int8 CPU inference)
    - PyAV (bundled transitive dep of faster-whisper, used for duration check)
  patterns:
    - WhisperModel loaded at lifespan startup via run_in_threadpool
    - threading.Lock serializes CTranslate2 inference (not thread-safe)
    - list(segments) inside lock block forces lazy generator evaluation
    - Two-layer 25MB size cap (Content-Length + streaming accumulator)
    - beam_size=1, best_of=1, temperature=0 for greedy/predictable CPU inference

key-files:
  created:
    - x402-transcription-api/main.py
    - x402-transcription-api/requirements.txt
    - x402-transcription-api/config.py
  modified: []

key-decisions:
  - "faster-whisper small model (466MB, ~852MB RAM int8): best CPU speed/quality tradeoff for pay-per-use API"
  - "PyAV for duration check — no system ffmpeg required (bundled via CTranslate2 transitive dep)"
  - "greedy decoding (beam_size=1, best_of=1, temperature=0) for predictable CPU memory on home server"
  - "WHISPER_CPU_THREADS=4 from config — must verify with sysctl -n hw.physicalcpu at deploy time"
  - "No deployment artifacts in Plan 01 — launchd plist, cloudflared config, nginx handled in Plan 02"

patterns-established:
  - "WhisperModel lifespan pattern: load via run_in_threadpool(lambda: WhisperModel(...)) at startup"
  - "CPU model lock: with _model_lock: segments, info = model.transcribe(...); segments_list = list(segments)"
  - "Two-layer audio download: Content-Length fast-reject + streaming chunk accumulator"

requirements-completed: [TRANS-01, TRANS-02, TRANS-03, TRANS-04, TRANS-05, TRANS-06]

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 9 Plan 01: Audio Transcription API Summary

**faster-whisper small/int8/CPU transcription service with x402 payment gate, SSRF-protected streaming download, PyAV duration check, and auto language detection**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-15T12:34:15Z
- **Completed:** 2026-03-15T12:37:14Z
- **Tasks:** 2
- **Files modified:** 3 (all created)

## Accomplishments

- Complete FastAPI transcription service with all 6 TRANS requirements implemented in 537-line main.py
- WhisperModel(small, cpu, int8, cpu_threads=4) loaded at startup via lifespan + run_in_threadpool; threading.Lock serializes CTranslate2 inference
- Two-layer 25MB streaming download cap (Content-Length fast-reject + chunk accumulator) plus redirect-chain SSRF re-validation hook
- PyAV duration check rejects audio > 10 minutes with clear error message; no system ffmpeg required
- Auto language detection (TRANS-02) + optional word-level timestamps via word_timestamps parameter (TRANS-03)
- Free GET /transcribe/test fixture endpoint matching real response shape, rate-limited 100/hour (TRANS-06)
- SSRF validation in SSRFMiddleware with path check correctly set to "/transcribe" (not "/scrape" — P13 mitigation)
- config.py separates tunable constants from service logic; requirements.txt pins all 7 dependencies

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project scaffold and configuration** - `5e1f52f` (chore)
2. **Task 2: Implement complete main.py with all service logic** - `80fef34` (feat)

**Plan metadata:** (added below after state update)

## Files Created/Modified

- `x402-transcription-api/main.py` - Complete FastAPI service (537 lines); all 6 TRANS requirements, SSRF middleware, WhisperModel lifespan, download, duration check, transcription, 4 endpoints
- `x402-transcription-api/requirements.txt` - 7 pinned dependencies
- `x402-transcription-api/config.py` - Configuration constants (MAX_AUDIO_BYTES, MAX_DURATION_SECONDS, WHISPER_MODEL, PRICE_PER_REQUEST, etc.)

## Decisions Made

- **faster-whisper small model**: 3.4% WER, ~852MB RAM int8, full multilingual, ~45-90s for 5min audio on Intel. Best CPU speed/quality tradeoff for a pay-per-use public API.
- **PyAV for duration check**: faster-whisper's CTranslate2 bundles PyAV as a transitive dependency — no system ffmpeg required. Avoids the PATH-in-launchd pitfall (P7).
- **Greedy decoding**: beam_size=1, best_of=1, temperature=0 prevents temperature fallback from multiplying CPU memory 3-5x on difficult audio (P3).
- **WHISPER_CPU_THREADS=4 in config**: Must be verified with `sysctl -n hw.physicalcpu` on the home server before deploy — exceeding physical cores causes OOM (P2).
- **No deployment artifacts**: launchd plist, cloudflared config, nginx — all deferred to Plan 02 as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None for Plan 01 — code only, no external services configured. Plan 02 handles deployment configuration (PAY_TO_ADDRESS env var, cloudflared tunnel, launchd plist).

## Next Phase Readiness

- `x402-transcription-api/` directory is complete and ready for deployment to home server (10.0.0.2)
- Plan 02 will add: launchd plist, cloudflared tunnel config, nginx (optional for LAN), and deploy script
- Before Plan 02 deploy: verify `sysctl -n hw.physicalcpu` on home server and update WHISPER_CPU_THREADS in config.py if != 4
- `fastapi-x402` macOS compatibility is an open question per RESEARCH.md — test first, hand-rolled fallback is documented if needed

---
*Phase: 09-audio-transcription-api*
*Completed: 2026-03-15*
