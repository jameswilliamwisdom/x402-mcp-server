---
phase: 08-email-sending-api
plan: "01"
subsystem: x402-email-api
tags: [fastapi, resend, email, x402, rate-limiting, pii-safe-logging]
dependency_graph:
  requires: []
  provides: [x402-email-api-service]
  affects: [x402-mcp-server-tools]
tech_stack:
  added: [resend>=2.0.0, pydantic[email]>=2.0.0]
  patterns: [fastapi-x402-payment-gate, per-wallet-rate-limit, per-domain-rate-limit, synchronous-sdk-plain-def, pii-safe-logging]
key_files:
  created:
    - x402-email-api/main.py
    - x402-email-api/requirements.txt
    - x402-email-api/Dockerfile
    - x402-email-api/railway.toml
  modified: []
decisions:
  - "Plain def route handler (not async def) for send_email — Resend SDK uses requests (synchronous); FastAPI auto-routes to thread pool"
  - "FROM_ADDRESS hardcoded to x402 Email API <noreply@jameswisdom.ink> — not user-configurable"
  - "DAILY_SEND_LIMIT=10 per wallet, DAILY_DOMAIN_LIMIT=5 per wallet/domain — single _wallet_lock for both dicts"
  - "Rate limit counters incremented BEFORE Resend call — prevents quota manipulation via induced failures"
  - "HTML body detection: starts with '<' and contains '</' or '/>' — omit 'text' key for HTML (Resend auto-generates)"
  - "ResendError caught and mapped: quota errors -> 503, rate limit -> 503, auth errors -> 500"
  - "log_send_event logs domain only (not full address) and SHA256 subject hash (not subject text)"
  - "No SSRFMiddleware — only outbound call is to api.resend.com (trusted third-party)"
  - "No fixture.json — GET /send/test returns inline fake message_id"
metrics:
  duration_seconds: 123
  completed_date: "2026-03-14"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 0
---

# Phase 8 Plan 01: Email API Build Summary

**One-liner:** FastAPI email service with Resend SDK integration, per-wallet/domain rate limiting, PII-safe logging, and x402 $0.01 payment gate.

## What Was Built

Complete `x402-email-api/` service directory ready for Docker build and Railway deployment. Follows the established Phase 5-7 pattern: FastAPI + fastapi-x402 + slowapi + per-wallet rate limit. The novelty is the Resend SDK integration which is synchronous (plain `def` route, not `async def`).

## Files Created

| File | Purpose | Key Details |
|------|---------|-------------|
| `x402-email-api/main.py` | Complete FastAPI service | 313 lines, all 5 requirements satisfied |
| `x402-email-api/requirements.txt` | Python dependencies | 6 deps, pydantic[email] for EmailStr |
| `x402-email-api/Dockerfile` | Docker build | python:3.11-slim, zero apt packages |
| `x402-email-api/railway.toml` | Railway deployment | healthcheckPath=/health, timeout=30 |

## Requirements Satisfied

| Req | Description | Implementation |
|-----|-------------|----------------|
| EMAIL-01 | Plain-text email sending | `build_send_params` sets `"text"` key for plain-text bodies |
| EMAIL-02 | HTML body with auto plain-text fallback | `build_send_params` sets `"html"` key only; Resend handles fallback server-side |
| EMAIL-03 | Verified sender domain hardcoded | `FROM_ADDRESS = "x402 Email API <noreply@jameswisdom.ink>"` constant |
| EMAIL-04 | Per-wallet 10/day rate limit | `check_and_increment_wallet_limit()` with `threading.Lock` |
| EMAIL-05 | Free test endpoint | `GET /send/test` returns `{"message_id": "test_00000000-..."}` inline |

## Architecture Decisions

**Synchronous route handler:** `def send_email` (not `async def`) because Resend SDK uses `requests` (blocking I/O). FastAPI auto-routes sync handlers to a thread pool — this is the correct pattern, simpler than `async def` + `run_in_threadpool`.

**Per-domain rate limit:** Added `check_and_increment_domain_limit` (5/wallet/domain/day) alongside the wallet limit. Uses the same `_wallet_lock` to prevent deadlock. Prevents a single wallet from hammering one recipient domain.

**HTML detection heuristic:** `stripped.startswith("<") and ("</" in stripped or "/>" in stripped)`. Covers standard HTML while treating edge cases (bare `<br>`) as plain text — conservative and correct.

**ResendError error mapping:**
- `daily_quota_exceeded` / `monthly_quota_exceeded` → 503 (caller not at fault)
- `rate_limit_exceeded` (Resend's 2 req/sec) → 503 (transient, not caller's fault)
- 401/403 → 500 (operator config error)
- All others → 500 with message

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

Files verified:
- `x402-email-api/main.py` — FOUND (313 lines, syntax valid)
- `x402-email-api/requirements.txt` — FOUND (6 deps)
- `x402-email-api/Dockerfile` — FOUND (python:3.11-slim)
- `x402-email-api/railway.toml` — FOUND (healthcheckPath=/health)

Commits verified:
- e16b11d — scaffold (requirements.txt, Dockerfile, railway.toml)
- c530a05 — main.py implementation
