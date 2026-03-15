# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1 — Universal Utility APIs

**Shipped:** 2026-03-15
**Phases:** 6 | **Plans:** 12

### What Was Built
- 5 new FastAPI backend services (scraping, conversion, search, email, transcription)
- 4 Railway deployments + 1 home server deployment with Cloudflare Tunnel
- MCP server expanded from 6 to 11 tools, published as v1.1.0 on npm
- All 29 requirements satisfied, all 10 E2E flows verified

### What Worked
- FastAPI + fastapi-x402 pattern proved highly reusable — each new API followed the same scaffold (main.py, Dockerfile, railway.toml, fixture.json)
- SSRF middleware copied and adapted cleanly between scraping, conversion, and transcription APIs
- Parallel research (MECE dimensions) caught integration pitfalls before execution (CTranslate2 thread safety, Playwright version pinning, PyAV bundling)
- Phase ordering was well-chosen — scraping first (highest risk) taught patterns reused in all later phases
- Email DNS propagation overlap with Phase 7 execution saved 48 hours of blocking

### What Was Inefficient
- Phases 6, 7, 8 executed before verification step was added to workflow — no VERIFICATION.md for 3 of 6 phases
- ROADMAP.md status markers didn't always get updated by phase-complete CLI (some phases showed "In Progress" or "Planning Complete" after completion)
- gsd-tools `commit-docs` command doesn't exist — had to fall back to manual git commands multiple times
- Summary frontmatter `requirements-completed` extraction via gsd-tools produced no output — had to grep manually

### Patterns Established
- **FastAPI service template:** main.py + Dockerfile + railway.toml + fixture.json + requirements.txt — proven across 5 services
- **SSRF dual-layer:** Pre-flight DNS check in middleware + httpx redirect re-validation hook — copy-paste between services
- **Per-wallet rate limiting:** Extract wallet from decoded_payment, threading.Lock for atomic check-and-increment, increment before upstream call
- **Discriminated union endpoint:** Single POST with Pydantic `Field(discriminator="type")` for multi-operation APIs
- **Cloudflare Tunnel for home server:** Zero router config, launchd persistence, public subdomain on managed domain
- **npm passkey auth:** iCloud Keychain + `--auth-type=web` — replaces TOTP authenticator app

### Key Lessons
1. Pin Playwright version to match Docker base image Chromium — pip resolves latest otherwise, causing silent failures
2. Railway startCommand does NOT expand shell variables — wrap in `sh -c '...'` for `${PORT}` expansion
3. CTranslate2 (faster-whisper) is NOT thread-safe — must serialize with threading.Lock AND force lazy generator evaluation inside the lock
4. PyAV bundles FFmpeg — no system ffmpeg required, and avoids launchd PATH pitfalls
5. LIFO middleware ordering matters — add payment FIRST, SSRF LAST, so SSRF runs before payment check

### Cost Observations
- Model mix: ~70% sonnet (executors, verifiers, researchers), ~30% opus (orchestration)
- 4-day timeline for 6 phases, 12 plans, 29 requirements
- Highest efficiency: Phase 7 (search API) — 2 minutes for Plan 01 build, lightest service in the project

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 4 | 9 | Established GSD workflow, package hardening, brand site |
| v1.1 | 6 | 12 | Added MECE research, verification step, integration checking |

### Top Lessons (Verified Across Milestones)

1. Ship the riskiest phase first — unknowns compress when tackled early (Playwright Docker in v1.1, package security in v1.0)
2. Reusable patterns compound — the FastAPI template saved hours across 5 services
3. Static analysis catches most issues — VERIFICATION.md found real bugs (TRANS-05 typo, BLOCKED_RESOURCE_TYPES duplication)
