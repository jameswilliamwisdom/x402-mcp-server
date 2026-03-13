---
phase: 05-web-scraping-api
plan: 02
subsystem: deployment
tags: [docker, railway, playwright, deployment, ssrf, smoke-test]

# Dependency graph
requires: [05-01]
provides:
  - x402-scraping-api deployed and verified on Railway
  - Production URL: https://x402-scraping-api-production.up.railway.app
  - All 4 smoke tests passing (health, root, fixture, SSRF)
affects: [10-mcp-update]

# Tech tracking
tech-stack:
  patterns:
    - Railway startCommand must wrap shell variable expansion in `sh -c` — Railway passes the string directly to the process, not through a shell
    - Dockerfile CMD should use exec-form with sh -c for ${PORT} expansion: CMD ["sh", "-c", "uvicorn ..."]
    - playwright pip package must be pinned to match Docker base image version (==1.44.0) — pip resolves to latest (1.58.0) which is incompatible with the base image's bundled Chromium

key-files:
  created: []
  modified:
    - x402-scraping-api/Dockerfile (CMD exec-form fix)
    - x402-scraping-api/railway.toml (sh -c wrapper fix)

key-decisions:
  - "Pin playwright==1.44.0 in requirements.txt to match Docker base image Chromium version (pip default resolved to 1.58.0, causing incompatibility)"
  - "Wrap startCommand in sh -c for Railway env var expansion — Railway does not pass startCommand through a shell"
  - "Memory cap set to 4GB (Railway minimum slider position) — actual usage is 300-400MB, billing is per-usage not per-cap"

requirements-completed: [SCRAPE-01, SCRAPE-02, SCRAPE-03, SCRAPE-04, SCRAPE-05]

# Metrics
duration: 25min
completed: 2026-03-12
---

# Phase 5 Plan 02: Docker Validation + Railway Deployment Summary

**Docker build validated locally, two bugs fixed (playwright version pin, shell expansion), deployed to Railway, all production endpoints verified**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-12T20:00:00Z
- **Completed:** 2026-03-12T21:15:00Z
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)

## Accomplishments

- Docker build validated locally — playwright pinned to ==1.44.0 (pip resolved to 1.58.0 which broke Chromium compatibility)
- Railway project created via CLI: `x402-scraping-api` (project ID: `d189652c-f7c4-4115-a274-e7647528e5f3`)
- Env vars set: `PAY_TO_ADDRESS`, `X402_NETWORK=base`
- Fixed `${PORT:-8000}` shell expansion bug — Railway startCommand doesn't go through a shell; wrapped in `sh -c`
- Memory cap set to 4GB (Railway's minimum slider value; actual usage ~300-400MB)
- All 4 smoke tests pass in production:
  - `GET /health` → `{"status":"healthy","browser":true}`
  - `GET /` → service info with pricing
  - `GET /scrape/test` → full fixture JSON (links, tables, images, metadata)
  - `POST /scrape` with `169.254.169.254` → 400 SSRF rejection

## Task Commits

1. **Task 1 (prior session):** `8a62703` — pin playwright==1.44.0 to match Docker base image
2. **Task 2 (this session):** `2a39a0f` — wrap start command in sh -c for Railway env var expansion

## Production Verification

| Endpoint | Method | Expected | Actual | Status |
|----------|--------|----------|--------|--------|
| `/health` | GET | `{"status":"healthy","browser":true}` | Match | PASS |
| `/` | GET | Service info JSON | Match | PASS |
| `/scrape/test` | GET | Full fixture JSON | Match | PASS |
| `/scrape` (SSRF) | POST | 400 SSRF error | Match | PASS |

## Railway Service Details

- **URL:** https://x402-scraping-api-production.up.railway.app
- **Project ID:** d189652c-f7c4-4115-a274-e7647528e5f3
- **Service ID:** fec13eee-5015-4462-aaaa-9fd1f5f77557
- **Environment:** production
- **Memory cap:** 4GB (Railway minimum)
- **Builder:** Dockerfile (auto-detected)

## Issues Encountered

1. **playwright version mismatch:** pip resolved playwright to 1.58.0 but the Docker base image (`v1.44.0-jammy`) bundles Chromium for 1.44.0. Fixed by pinning `playwright==1.44.0` in requirements.txt.
2. **Railway startCommand shell expansion:** `${PORT:-8000}` passed literally to uvicorn (not expanded). Railway does not interpret startCommand through a shell. Fixed by wrapping in `sh -c '...'`.

## Deviations from Plan

- Memory set to 4GB instead of 1GB — Railway's dashboard slider has a minimum of 4GB (UI constraint, not a billing concern since Railway charges per actual usage).

## Next Phase Readiness

- Phase 5 complete — all SCRAPE requirements verified in production
- Railway URL recorded for Phase 10 MCP integration: `https://x402-scraping-api-production.up.railway.app`
- Phase 6 (File Conversion API) is next

---
*Phase: 05-web-scraping-api*
*Completed: 2026-03-12*
