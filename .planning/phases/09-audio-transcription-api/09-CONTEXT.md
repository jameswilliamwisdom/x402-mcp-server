# Phase 9: Audio Transcription API - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

A self-hosted FastAPI service on the home Mac server (10.0.0.2, macOS Monterey, Intel x86_64) at port 8889. Accepts an audio file URL, downloads it, and transcribes via `faster-whisper` with `compute_type="int8"`. Returns transcript text, detected language, and optional segment timestamps. x402 micropayment gating. nginx proxies port 8889. A launchd plist persists the process across reboots. Cloudflare Tunnel provides public access.

</domain>

<decisions>
## Implementation Decisions

### Public Access
- Cloudflare Tunnel (not port forwarding) — zero router config, no exposed home IP
- Public URL: `transcribe.jameswisdom.ink` (subdomain of existing Cloudflare-managed domain)
- `cloudflared` not yet installed on home server — install via Homebrew during setup
- Tunnel routes `transcribe.jameswisdom.ink` → `localhost:8889`

### Server Environment
- Home server: 10.0.0.2, Intel x86_64, macOS Monterey — confirmed accurate
- Python 3 and Homebrew already installed
- Port 8889 is free and available
- ffmpeg status unknown — check and install via Homebrew if missing (`brew install ffmpeg`)
- `faster-whisper` with `compute_type="int8"` (Intel x86_64 — no MLX/Apple Silicon)

### Payment Middleware
- Try `fastapi-x402` first (same as Railway services) — it may work fine on macOS
- If fastapi-x402 fails on macOS: fall back to hand-rolled middleware validating X-PAYMENT header against `https://x402.org/facilitator/verify`
- Same USDC wallet (PAY_TO_ADDRESS) as all Railway services — one wallet for the entire x402 network

### Audio Input & Limits
- Input: URL only (no file uploads) — consistent with scraping/conversion API pattern
- File size limit: 25MB
- Duration limit: 10 minutes (ffprobe check before transcription)
- 300-second subprocess timeout on transcription
- SSRF validation on input audio URL

### Claude's Discretion
- faster-whisper model size — pick best speed/quality tradeoff for Intel x86_64 pay-per-use API
- USDC price per transcription — factor in compute cost (50-100s per 5min audio on Intel)
- Facilitator-down behavior — decide based on security posture
- Word-level vs segment-level timestamps — decide based on API usefulness
- Free test endpoint fixture format

</decisions>

<specifics>
## Specific Ideas

- Cloudflare Tunnel eliminates all router/firewall complexity — just `cloudflared tunnel` daemon
- launchd plist at `~/Library/LaunchAgents/com.x402.transcription.plist` for process persistence
- nginx reverse proxy on the same machine (port 80/443 → 8889)
- The production URL `transcribe.jameswisdom.ink` is what goes into `src/index.ts` APIS dict in Phase 10

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-audio-transcription-api*
*Context gathered: 2026-03-14*
