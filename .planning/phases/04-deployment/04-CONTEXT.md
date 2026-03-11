# Phase 4: Deployment - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deploy the built static site (`site/dist/`) to a home Mac server via rsync. Configure nginx to serve it. Start on local network over HTTP — domain, TLS, and public access are deferred to a future phase.

</domain>

<decisions>
## Implementation Decisions

### Server & Access
- Home server running macOS at `10.0.0.2`
- SSH access: `ssh jameswisdom@10.0.0.2` (key-based auth already configured)
- Target directory: `/var/www/x402-network/`
- nginx — may or may not be installed already (check during execution, install via Homebrew if missing)
- Port forwarding status unknown — not needed for local-only access

### Domain & DNS
- No domain for v1 — serve on IP address only (`http://10.0.0.2`)
- HTTP only — no TLS (Let's Encrypt requires a domain)
- Start local network only, go public later
- Public IP type (static vs dynamic) unknown — not relevant until going public

### TLS & Security
- HTTP-only for now — TLS deferred until domain is purchased
- Future plan: Cloudflare proxy for TLS + CDN + IP hiding
- nginx must deny all dotfile paths (`/.planning/`, `/.git/`, `/.env`, etc.) — defense in depth
- Standard security headers: X-Frame-Options, X-Content-Type-Options, Referrer-Policy

### Deploy Workflow
- `site/deploy.sh` — builds (`npm run build`) + rsyncs `dist/` to server
- Separate one-time `site/setup-server.sh` for nginx install + config on the server
- Automated smoke tests in deploy.sh — curl key pages, check status codes, verify OG tags
- No CI/CD — manual deploys via script

### Claude's Discretion
- OG image site URL handling (currently `https://x402.todo` placeholder) — Claude decides whether to update to local IP or leave as placeholder
- nginx config details (worker_processes, gzip, cache headers)
- Exact smoke test assertions
- Whether setup-server.sh runs locally or is copied to server and run there

</decisions>

<specifics>
## Specific Ideas

- The roadmap specifies `rsync -av --delete site/dist/ user@homeserver:/var/www/x402-network/` as the deploy command
- Smoke tests should check: homepage returns 200, `/.planning/` returns 404, docs pages load, OG meta tags present
- nginx `try_files $uri $uri/ /index.html;` for SPA-style fallback routing

</specifics>

<deferred>
## Deferred Ideas

- Domain purchase and DNS setup — separate effort when ready to go public
- TLS via Cloudflare proxy — requires domain first
- Port forwarding for public internet access — after local deployment is verified
- CI/CD pipeline — overkill for a single-person project at v1
- DDNS for dynamic IP — only needed if going public without a static IP

</deferred>

---

*Phase: 04-deployment*
*Context gathered: 2026-03-11*
