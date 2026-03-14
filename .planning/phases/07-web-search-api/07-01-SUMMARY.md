---
phase: 07-web-search-api
plan: 01
subsystem: api
tags: [fastapi, tavily, x402, python, search, rate-limiting, slowapi, asyncio]

# Dependency graph
requires:
  - phase: 05-web-scraping-api
    provides: middleware ordering pattern (init_x402 + CORS), @pay decorator pattern, slowapi fixture endpoint pattern
  - phase: 06-file-conversion-api
    provides: python:3.11-slim Dockerfile pattern, CORS setup
provides:
  - x402-search-api FastAPI service (5 files) wrapping Tavily with per-wallet daily rate limit
  - AsyncTavilyClient integration with content->snippet field rename
  - Per-wallet 50 queries/day rate limit using threading.Lock and decoded_payment extraction
  - Free GET /search/test fixture endpoint with slowapi 100/hour IP rate limit
  - SEARCH-01 through SEARCH-05 requirements satisfied
affects: [08-email-sending-api, 09-audio-transcription-api, 10-mcp-server-update]

# Tech tracking
tech-stack:
  added: [tavily-python>=0.5.0,<0.6.0, AsyncTavilyClient]
  patterns:
    - per-wallet daily rate limit via decoded_payment["payload"]["authorization"]["from"]
    - threading.Lock for in-memory wallet counter atomicity
    - content->snippet field rename in response shaping
    - increment-before-call (not after) to prevent quota manipulation via induced failures

key-files:
  created:
    - x402-search-api/main.py
    - x402-search-api/requirements.txt
    - x402-search-api/Dockerfile
    - x402-search-api/railway.toml
    - x402-search-api/fixture.json
  modified: []

key-decisions:
  - "Per-wallet check is inside route handler body (after @pay sets decoded_payment), not in middleware"
  - "search_depth always basic (1 credit), include_answer always bool not string — prevents 2-credit overage"
  - "Increment wallet counter BEFORE calling Tavily — user paid, attempt counts regardless of upstream failure"
  - "No SSRFMiddleware — only outbound call is to trusted api.tavily.com, no user-supplied URLs"
  - "AsyncTavilyClient (not sync TavilyClient) — avoids blocking the FastAPI event loop"

patterns-established:
  - "Per-wallet rate limit pattern: extract wallet from decoded_payment after @pay, threading.Lock + dict for atomic check-and-increment"
  - "Response shaping: Tavily returns content, API returns snippet — rename at run_search boundary"

requirements-completed: [SEARCH-01, SEARCH-02, SEARCH-03, SEARCH-04, SEARCH-05]

# Metrics
duration: 2min
completed: 2026-03-13
---

# Phase 7 Plan 01: Web Search API Summary

**FastAPI search service wrapping AsyncTavilyClient with per-wallet 50 queries/day rate limit, content->snippet response shaping, and free fixture test endpoint — lightest service in the project (6 Python deps, no browser, no C libs)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-13T23:59:58Z
- **Completed:** 2026-03-14T00:01:44Z
- **Tasks:** 2
- **Files created:** 5

## Accomplishments
- Complete `x402-search-api/` directory ready for Docker build and Railway deployment
- AsyncTavilyClient integration with `run_search()` that renames Tavily's `content` field to `snippet`
- Per-wallet daily rate limit: extracts wallet from `decoded_payment["payload"]["authorization"]["from"]`, uses `threading.Lock` for atomic check-and-increment
- Free GET /search/test endpoint returning fixture JSON (100/hour IP rate limit via slowapi)
- Minimal Docker image: python:3.11-slim, zero apt packages, pure pip install

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project scaffold and configuration files** - `b094513` (feat)
2. **Task 2: Implement complete main.py with Tavily integration and per-wallet rate limiting** - `1a7634d` (feat)

## Files Created/Modified
- `x402-search-api/main.py` - Complete FastAPI service (266 lines): Tavily integration, per-wallet rate limit, all 4 route handlers
- `x402-search-api/requirements.txt` - 6 Python dependencies (fastapi, uvicorn, pydantic, fastapi-x402, tavily-python, slowapi)
- `x402-search-api/Dockerfile` - python:3.11-slim, zero apt packages, shell-form CMD for PORT expansion
- `x402-search-api/railway.toml` - Railway deployment config with healthcheckTimeout=30 (no browser startup delay)
- `x402-search-api/fixture.json` - Free test endpoint fixture with snippet field (not content), 3 x402-themed results

## Decisions Made
- Per-wallet check placed inside route handler (after `@pay` runs and sets `decoded_payment`), not in middleware — `decoded_payment` is only available post-payment
- `search_depth` hardcoded to `"basic"` (1 Tavily credit = $0.008) and `include_answer` always `bool` (never `"advanced"`) — prevents 2-credit overages that would make $0.01 endpoint unprofitable
- Wallet counter incremented BEFORE calling Tavily — user paid, the attempt counts against quota regardless of Tavily upstream failures
- No SSRFMiddleware — only outbound call is to trusted `api.tavily.com`, there are no user-supplied URLs to validate
- `AsyncTavilyClient` instead of sync `TavilyClient` — avoids blocking the FastAPI event loop on Tavily HTTP calls

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None at this stage — Phase 02 (Railway deployment) will require `TAVILY_API_KEY` environment variable in Railway dashboard.

## Next Phase Readiness

- `x402-search-api/` directory is complete with all 5 files, ready for Phase 02 Docker build + Railway deployment
- `TAVILY_API_KEY` environment variable must be set in Railway before deployment
- The per-wallet rate limit uses in-memory storage (resets on pod restart) — acceptable for v1.1, noted for future persistence decision

---
*Phase: 07-web-search-api*
*Completed: 2026-03-13*
