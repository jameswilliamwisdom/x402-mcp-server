---
phase: 06-file-conversion-api
plan: 01
subsystem: api
tags: [fastapi, python, pillow, weasyprint, httpx, x402, ssrf, railway, docker]

# Dependency graph
requires:
  - phase: 05-web-scraping-api
    provides: SSRF validation pattern, SSRFMiddleware ordering, @pay decorator pattern, fixture endpoint pattern
provides:
  - x402-conversion-api/ directory with 5 deployment-ready files
  - FastAPI service with Pillow image resize/reformat (CONV-01)
  - CSV-to-JSON converter via Python stdlib (CONV-02)
  - HTML-to-PDF converter via WeasyPrint (CONV-03)
  - SSRF protection on all file fetch URLs (CONV-04)
  - Free test endpoint with fixture data (CONV-05)
affects: [07-web-search-api, 08-email-sending-api, 10-mcp-server-update]

# Tech tracking
tech-stack:
  added: [Pillow>=12.0.0, weasyprint>=68.1, httpx>=0.27.0, slowapi>=0.1.9, fastapi-x402>=0.1.8]
  patterns:
    - "Pydantic discriminated union: single POST /convert endpoint with type field dispatching to 3 converters"
    - "httpx async streaming download with event_hooks for redirect SSRF re-validation"
    - "run_in_threadpool wrapping all sync CPU-bound conversions (Pillow, WeasyPrint, CSV)"
    - "WeasyPrint safe_url_fetcher: SSRF validation on all secondary fetches (CSS, images, @import)"
    - "Docker build-time WeasyPrint smoke test: catches missing C libs at build time not runtime"

key-files:
  created:
    - x402-conversion-api/main.py
    - x402-conversion-api/requirements.txt
    - x402-conversion-api/Dockerfile
    - x402-conversion-api/railway.toml
    - x402-conversion-api/fixture.json

key-decisions:
  - "Single POST /convert endpoint with Pydantic discriminated union on type field — unified payment gating, SSRF, and test fixture under one path"
  - "python:3.11-slim base image — 130MB vs 1.5GB Playwright image; no browser needed for this service"
  - "12-package apt layer confirmed for WeasyPrint system deps; build-time smoke test prevents silent runtime failures"
  - "SSRF re-validation on httpx redirect chain via event_hooks — prevents TOCTOU bypass where server redirects to private IP after initial validation"
  - "safe_url_fetcher wrapping WeasyPrint default_url_fetcher — mitigates CVE-2025-68616 (SSRF via internal url_fetcher redirect)"
  - "Output size guard before base64 encoding — saves ~33% memory on large outputs"

patterns-established:
  - "Discriminated union pattern: ConvertRequest = Annotated[Union[...], Field(discriminator='type')] — single endpoint for multi-operation APIs"
  - "Sync converter isolation: define as def sync_X(), call via await run_in_threadpool(sync_X, ...) — keeps async handler clean"
  - "Redirect SSRF re-validation: httpx event_hooks={'response': [on_redirect]} with validate_url_for_ssrf(location) per hop"

requirements-completed: [CONV-01, CONV-02, CONV-03, CONV-04, CONV-05]

# Metrics
duration: 3min
completed: 2026-03-13
---

# Phase 6 Plan 01: File Conversion API — Build Service Summary

**FastAPI file conversion service with Pillow image resize/reformat, stdlib CSV-to-JSON, and WeasyPrint HTML-to-PDF unified under a single Pydantic discriminated union endpoint with SSRF protection and streaming httpx download**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T02:56:58Z
- **Completed:** 2026-03-13T02:59:49Z
- **Tasks:** 2 completed
- **Files modified:** 5

## Accomplishments

- Built complete `x402-conversion-api/` service (5 files) ready for Docker build and Railway deployment
- Implemented three converters: Pillow image (CVE-2025-48379 safe, decompression bomb guard, JPEG alpha composite), CSV-to-JSON (utf-8-sig BOM, Sniffer delimiter, latin-1 fallback), WeasyPrint HTML-to-PDF (CVE-2025-68616 safe, safe_url_fetcher)
- Established new discriminated union pattern for multi-operation single-endpoint APIs — reusable for future phases

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project scaffold and configuration files** - `8155ed3` (feat)
2. **Task 2: Implement complete main.py with all conversion logic** - `2dae347` (feat)

**Plan metadata:** (committed with docs commit below)

## Files Created/Modified

- `x402-conversion-api/main.py` — Complete 523-line FastAPI service: SSRF validation, httpx streaming download, 3 sync converters, SSRFMiddleware, x402 payment, discriminated union request model, 4 route handlers
- `x402-conversion-api/requirements.txt` — 8 Python dependencies (Pillow>=12.0.0, weasyprint>=68.1, httpx>=0.27.0, fastapi-x402>=0.1.8, slowapi, fastapi, uvicorn, pydantic)
- `x402-conversion-api/Dockerfile` — python:3.11-slim with 12-package apt layer for WeasyPrint system deps + build-time smoke test
- `x402-conversion-api/railway.toml` — healthcheckPath=/health, healthcheckTimeout=30, ON_FAILURE restart policy
- `x402-conversion-api/fixture.json` — 1x1 transparent PNG base64 with full response envelope (success, type, mime_type, data, warnings)

## Decisions Made

- **Single endpoint design:** `POST /convert` with `type` discriminator field rather than three separate endpoints (`/convert/image`, `/convert/csv`, `/convert/html`). All three operations share the identical pipeline (validate → download → convert → base64 → return), so a single endpoint unifies payment gating, SSRF middleware path, and test fixture under one path.
- **python:3.11-slim base image:** 130MB vs 1.5GB Playwright image from Phase 5. No browser needed. Confirmed Debian bookworm ships Pango 1.50.x (above WeasyPrint's 1.44.0 minimum).
- **WeasyPrint safe_url_fetcher:** Wraps `default_url_fetcher` with SSRF validation on every secondary resource fetch (CSS, images, @import). Required for CVE-2025-68616 mitigation — pre-flight validation alone has TOCTOU bypass via HTTP redirect.
- **httpx redirect SSRF re-validation:** `event_hooks={"response": [on_redirect]}` re-validates Location header on every redirect hop. Prevents server-controlled redirect to private IP after passing initial SSRF check.
- **Output size guard before base64:** `len(output_bytes) > MAX_OUTPUT_BYTES` check before `b64encode()` — saves ~33% memory on large outputs and gives callers a clear error before the expensive encoding step.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required for this plan. Railway deployment is handled in a separate plan (06-02 if planned).

## Next Phase Readiness

- `x402-conversion-api/` is complete with all 5 files. Ready for Docker build validation and Railway deployment.
- All 5 requirements satisfied: CONV-01 (image), CONV-02 (CSV), CONV-03 (HTML-to-PDF), CONV-04 (SSRF), CONV-05 (test endpoint).
- No blockers. Phase 7 (Web Search API) can proceed independently.

---
*Phase: 06-file-conversion-api*
*Completed: 2026-03-13*
