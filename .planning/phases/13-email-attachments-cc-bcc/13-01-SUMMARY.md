---
phase: 13-email-attachments-cc-bcc
plan: 01
subsystem: api
tags: [fastapi, pydantic, resend, email, attachments, base64, rate-limiting]

# Dependency graph
requires:
  - phase: 08-email-sending-api
    provides: existing EmailRequest model, build_send_params, domain rate limiter patterns
provides:
  - AttachmentItem Pydantic model with base64 validation, filename sanitization, MIME type validation
  - Extended EmailRequest with optional cc (List[EmailStr]), bcc (List[EmailStr]), attachments (List[AttachmentItem])
  - Extended build_send_params conditionally adding cc, bcc, attachments to Resend SDK params
  - Extended domain rate limiter covering all recipients (to + cc + bcc)
affects: [13-02-mcp-tool-extension, phase-16-mcp-publish]

# Tech tracking
tech-stack:
  added: [base64 (stdlib), mimetypes (stdlib), re (stdlib), List from typing, field_validator from pydantic]
  patterns:
    - "AttachmentItem nested model with @field_validator for complex validation logic"
    - "Conditional params building: if body.X: params['X'] = ... (never set None)"
    - "all_recipients list collects to + cc + bcc for rate limit iteration"
    - "mimetypes.guess_type(filename) for content_type auto-derivation"

key-files:
  created: []
  modified:
    - x402-email-api/main.py

key-decisions:
  - "Attachment size check uses decoded byte length (len(base64.b64decode(v))), NOT string length — base64 33% expansion means string length check would reject 18.7MB files as oversized"
  - "base64 string passed directly to Resend SDK content field — no decode/re-encode; Resend accepts Union[List[int], str] not bytes"
  - "List[EmailStr] (not List[str]) for cc/bcc — email-validator rejects CRLF injection characters automatically"
  - "domain rate limiter extended to all_recipients loop — prevents CC/BCC domain bypass where caller uses throwaway primary recipient"
  - "path field intentionally omitted from AttachmentItem — SSRF risk, Out of Scope per REQUIREMENTS.md"

patterns-established:
  - "field_validator order matters: filename and content_type validators run before content validator"
  - "Auto-derive content_type from mimetypes.guess_type when caller omits it; omit entirely if unknown extension"

requirements-completed: [EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04]

# Metrics
duration: 2min
completed: 2026-03-17
---

# Phase 13 Plan 01: Email Attachments + CC/BCC Backend Summary

**AttachmentItem model with base64 decode + byte-length validation, MIME injection protection, and filename sanitization; EmailRequest extended with cc/bcc/attachments; domain rate limiter covers all recipients**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-17T04:14:23Z
- **Completed:** 2026-03-17T04:17:03Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added AttachmentItem Pydantic model with three field validators: filename path-traversal sanitization via os.path.basename, MIME type CRLF injection protection via regex, and base64 validity + 25MB decoded byte-length cap
- Extended EmailRequest with optional cc (List[EmailStr]), bcc (List[EmailStr]), and attachments (List[AttachmentItem]) — all optional, backward compatible
- Extended build_send_params to conditionally include cc, bcc, attachments (never sets None keys); auto-derives content_type from filename extension when caller omits it
- Extended domain rate limiter to check all recipients (to + cc + bcc) via all_recipients loop — prevents CC/BCC domain rate limit bypass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add AttachmentItem model and extend EmailRequest** - `a5f80a4` (feat)
2. **Task 2: Extend build_send_params, domain rate limiter, and route handler** - `4c177c6` (feat)

## Files Created/Modified

- `x402-email-api/main.py` - Extended with AttachmentItem model, cc/bcc/attachments on EmailRequest, updated build_send_params, and all_recipients rate limit loop

## Decisions Made

- Decoded byte length check for 25MB cap: `len(base64.b64decode(v, validate=True)) > MAX_ATTACHMENT_BYTES` — base64 string is 33% larger than raw bytes so checking string length would incorrectly reject 18.7MB files
- base64 string passed directly as `content` to Resend SDK — Resend accepts `Union[List[int], str]`, not Python `bytes`; bytes would raise TypeError during JSON serialization
- `List[EmailStr]` for cc/bcc fields: Pydantic's email-validator rejects control characters including CRLF, preventing header injection via CC/BCC addresses
- `path` field omitted from AttachmentItem: SSRF risk, explicitly Out of Scope in REQUIREMENTS.md; only base64 content accepted

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

Test environment required `PAY_TO_ADDRESS` env var and `pydantic[email]`, `fastapi-x402`, `slowapi` installed globally to run verification inline. Tests were run with `PAY_TO_ADDRESS=0x0000000000000000000000000000000000000001` dummy value. No code changes required — env setup only.

## User Setup Required

None — no external service configuration required. Railway deployment already has `PAY_TO_ADDRESS` set.

## Next Phase Readiness

- Backend fully ready: `/send` endpoint accepts cc, bcc, attachments via validated Pydantic models
- Plan 13-02 can extend the MCP tool Zod schema (src/index.ts) to expose these fields to MCP callers
- No blockers

---
*Phase: 13-email-attachments-cc-bcc*
*Completed: 2026-03-17*
