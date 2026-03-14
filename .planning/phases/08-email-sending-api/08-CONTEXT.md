# Phase 8: Email Sending API - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

A new Railway service (`x402-email-api`) that sends transactional email via the Resend SDK. Accepts `to`, `subject`, and `body` (plain text or HTML). Returns a Resend message ID. Fixed verified sender domain; per-wallet daily send limit prevents abuse. Free test endpoint returns fake message ID without real delivery.

</domain>

<decisions>
## Implementation Decisions

### Sender Identity
- Domain: `x402.org` — verified via Resend
- From address: `x402 Email API <noreply@x402.org>`
- Optional `reply_to` parameter — caller can set a reply-to address so recipients can respond to them directly
- From address is hardcoded, not user-configurable

### Email Content
- Accept HTML body with auto-generated plain-text fallback (matches roadmap spec)
- No file attachments in v1 — defer to v1.2
- Pass HTML through raw to Resend — email clients don't execute scripts; Resend handles reputation

### Claude's Discretion
- Max body size limit — pick a reasonable ceiling for transactional email
- HTML sanitization approach — decide based on security best practices
- Per-recipient rate limit — decide whether to add one beyond the per-wallet limit, based on threat model for micropayment-gated APIs

### Abuse Prevention
- Email format validation only (regex) — Resend handles deliverability/bounces
- No content-based filtering — the USDC payment gate ($0.01+/email) is the economic spam deterrent
- Send logs to stdout/Railway logs (wallet address, recipient domain, subject hash) — server-side only, no queryable endpoint
- Per-wallet rate limit: 10 sends/day (from roadmap)

### Resend Configuration
- Resend free tier (100 emails/day, 1 domain) — sufficient for micropayment-gated API
- DNS provider for x402.org: TBD — determine during setup
- Resend account: needs to be created
- DNS verification (SPF/DKIM/DMARC) to be started immediately — absorb 24-48hr propagation before code deploys

</decisions>

<specifics>
## Specific Ideas

- Start Resend domain verification NOW (before planning/execution) so DNS propagates in time for deployment
- Follow same FastAPI + fastapi-x402 pattern as Phases 5-7
- Same per-wallet rate limit extraction pattern: `decoded_payment["payload"]["authorization"]["from"]`

</specifics>

<deferred>
## Deferred Ideas

- File attachments — v1.2
- Queryable audit log endpoint — future phase if needed
- Multiple sender domains — future phase
- Email templates / merge tags — future phase

</deferred>

---

*Phase: 08-email-sending-api*
*Context gathered: 2026-03-14*
