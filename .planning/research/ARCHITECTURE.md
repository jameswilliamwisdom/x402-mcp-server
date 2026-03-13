# Architecture Research

**Domain:** v1.1 Universal Utility APIs — 5 new backends integrating with existing x402 MCP server
**Researched:** 2026-03-12
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MCP Client (Claude Desktop, etc.)                   │
│              npx -y x402-mcp-server  |  X402_PRIVATE_KEY env var             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ stdio / MCP protocol
┌──────────────────────────────────────┴──────────────────────────────────────┐
│                        x402 MCP Server (src/index.ts)                        │
│                 TypeScript, @modelcontextprotocol/sdk, x402-fetch             │
│                                                                               │
│  EXISTING TOOLS (v1.0)            NEW TOOLS (v1.1)                           │
│  ─────────────────────────        ──────────────────────────────────────     │
│  x402_network_info (free)         x402_scrape (free+paid)                   │
│  x402_screenshot (free+paid)      x402_email_send (paid only)               │
│  x402_pdf_extract (free+paid)     x402_search (free+paid)                   │
│  x402_sentiment (free+paid)       x402_convert_file (free+paid)             │
│  x402_market_overview (free+paid) x402_transcribe (free+paid)               │
│  x402_intelligence (free+paid)                                               │
└──────────┬──────────────────────────────────────────────────────────────────┘
           │ HTTP via x402-fetch (handles 402 → USDC payment automatically)
           │
     ┌─────┴──────────────────────────────────────────────────────────────┐
     │                     API Layer (two hosting patterns)                │
     │                                                                     │
     │  ── Railway (existing) ──────────────────────────────────────────  │
     │  Screenshot API    PDF API    Sentiment API                         │
     │  FastAPI + fastapi-x402 + payment enforcement                       │
     │                                                                     │
     │  ── Railway (new) ──────────────────────────────────────────────── │
     │  Scraping API      Email API   Search API   File Conversion API     │
     │  FastAPI + fastapi-x402 (same proven pattern)                       │
     │                                                                     │
     │  ── Home Server (new, self-hosted) ──────────────────────────────  │
     │  Transcription API (10.0.0.2)                                       │
     │  FastAPI + custom x402 middleware (not fastapi-x402 library)        │
     │  nginx reverse proxy → uvicorn process, port 8889                  │
     │  MLX Whisper (macOS x86_64, runs natively)                         │
     └─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `src/index.ts` | MCP server — registers all tools, routes free vs paid calls | Modified — add 5 new tool registrations, expand APIS dict |
| Railway Scraping API | URL → structured JSON (text, links, tables, metadata) | New Railway service — Python/FastAPI + Playwright headless + Cheerio-equivalent (BeautifulSoup) |
| Railway Email API | Stateless transactional email send via Resend | New Railway service — Python/FastAPI + Resend SDK + fastapi-x402 |
| Railway Search API | Query → top N results as structured JSON | New Railway service — Python/FastAPI + search backend (TBD) + fastapi-x402 |
| Railway File Conversion API | Format-to-format: doc-to-pdf, image resize, html-to-pdf, csv-to-json | New Railway service — Python/FastAPI + conversion libs + fastapi-x402 |
| Home Server Transcription API | Audio URL → text transcript via MLX Whisper | New home-hosted service — Python/FastAPI + MLX Whisper + custom x402 middleware, nginx port 8889 |
| nginx (home server) | Reverse proxy for both brand site (8888) and transcription API (8889) | Existing nginx — add new server block for transcription |

---

## New vs Modified Components

### Modified (existing files change)

| File | What Changes | Why |
|------|-------------|-----|
| `src/index.ts` | Add 5 new entries to `APIS` dict, add ~5 new `server.tool()` blocks | New tools must be registered with the MCP server |
| `package.json` | Bump version to `1.1.0`, expand `keywords` | SemVer for new tools, discoverability |

### New (net new files/services)

| Component | Location | What It Is |
|-----------|----------|------------|
| Scraping API | New Railway service repo (or `~/projects/x402-scraping-api/`) | Python FastAPI service |
| Email API | New Railway service repo | Python FastAPI service |
| Search API | New Railway service repo | Python FastAPI service |
| File Conversion API | New Railway service repo | Python FastAPI service |
| Transcription API | `~/projects/x402-transcription-api/` | Python FastAPI service, home-hosted |
| nginx block | `/etc/nginx/sites-available/` on 10.0.0.2 | New `server` block for transcription at port 8889 |

---

## Recommended Project Structure

### MCP Server (modified `src/index.ts`)

```
src/
└── index.ts          # Add new APIS entries + 5 new server.tool() blocks
                      # All tools stay in one file through ~16 tools (acceptable)
```

When the file exceeds ~600 lines or ~10 APIs, extract to:

```
src/
├── index.ts          # thin entry — server setup + connect transport
├── tools/
│   ├── screenshot.ts
│   ├── pdf.ts
│   ├── sentiment.ts
│   ├── scrape.ts
│   ├── email.ts
│   ├── search.ts
│   ├── convert.ts
│   └── transcribe.ts
└── lib/
    ├── fetch.ts      # getPaidFetch(), apiGet(), apiPost()
    └── helpers.ts    # textResult(), errorResult(), checkHealth()
```

Do NOT refactor to modules as part of v1.1 — the file structure change is a separate concern. Get the new tools working first.

### Railway API Services (new)

Each Railway API follows the same file layout:

```
x402-<name>-api/
├── main.py           # FastAPI app, routes, x402 payment enforcement
├── requirements.txt  # fastapi, uvicorn, fastapi-x402, service-specific deps
├── Procfile          # web: uvicorn main:app --host 0.0.0.0 --port $PORT
└── railway.toml      # Railway config (optional, can use env vars)
```

### Home Server Transcription API (new, distinct layout)

```
~/projects/x402-transcription-api/
├── main.py           # FastAPI app, MLX Whisper call, custom x402 middleware
├── x402_middleware.py  # Hand-rolled x402 payment verification (no fastapi-x402)
├── requirements.txt  # fastapi, uvicorn, mlx-whisper, requests
├── start.sh          # uvicorn main:app --host 127.0.0.1 --port 8889
└── launchd/
    └── com.x402.transcription.plist  # macOS launchd service definition
```

---

## Architectural Patterns

### Pattern 1: Railway Service — fastapi-x402 (proven pattern, replicate 4x)

**What:** A FastAPI app with fastapi-x402 middleware applied to paid endpoints. Free test endpoints bypass middleware. Railway handles deployment, scaling, and SSL.

**When to use:** All four new Railway services (scraping, email, search, file conversion).

**Trade-offs:** No custom infrastructure work. Cold starts on Railway Hobby tier (first request after idle may take 2–5s). Payment verification is handled by the library — no crypto code to write. Each service is fully independent: separate deploy, separate URL, separate Railway project.

**Example (scraping API skeleton):**

```python
from fastapi import FastAPI, Request
from fastapi_x402 import X402Middleware

app = FastAPI()

# Paid endpoint — x402 middleware enforces payment
app.add_middleware(
    X402Middleware,
    payment_required_paths=["/scrape"],
    price_usd=0.01,
    wallet_address="0x6b21227Ca9Bb3590BB62ff60BA0EFbBf9Ba22ACC",
    network="base",
)

@app.get("/test/scrape")
async def test_scrape(url: str):
    # Free — hardcoded to example.com, httpbin.org, example.org
    ...

@app.get("/scrape")
async def scrape(url: str):
    # Paid — x402 middleware handles 402 → payment before this runs
    ...
```

**MCP tool pattern (mirroring existing tools):**

```typescript
const APIS = {
  // ... existing ...
  scrape: {
    name: "Web Scraping API",
    baseUrl: "https://x402-scraping-api-production.up.railway.app",
    price: "$0.01",
    description: "Scrape URLs and extract structured content",
    usesX402: true,
  },
  // ...
} as const;

server.tool(
  "x402_scrape",
  `Scrape a URL and return structured content...
Price: $0.01 USDC per scrape.`,
  {
    url: z.string().url().describe("URL to scrape"),
    extract: z.enum(["text", "links", "tables", "full"]).default("full"),
  },
  async (params) => {
    const base = APIS.scrape.baseUrl;
    try {
      const usePaid = !!PRIVATE_KEY;
      const endpoint = usePaid ? "/scrape" : "/test/scrape";
      const data = await apiGet(base, `${endpoint}?url=${encodeURIComponent(params.url)}&extract=${params.extract}`, usePaid);
      return textResult({ mode: usePaid ? "paid" : "free_test", cost: usePaid ? "$0.01" : "free", ...data });
    } catch (err: any) {
      return errorResult(err.message);
    }
  }
);
```

### Pattern 2: Self-Hosted Transcription — Custom x402 Middleware

**What:** A FastAPI app on the home Mac server where x402 payment verification is implemented manually (not via fastapi-x402 library, which assumes a Railway-compatible environment and may have OS-specific deps). nginx reverse-proxies the local uvicorn process. A macOS launchd plist keeps the process alive across reboots.

**When to use:** Transcription service only — any service where Railway costs are prohibitive due to compute intensity (GPU/model inference) and local hardware already has the required capability (MLX Whisper runs natively on Apple Silicon or x86_64 macOS).

**Trade-offs vs Railway pattern:**

| Concern | Railway Pattern | Home Server Pattern |
|---------|-----------------|---------------------|
| x402 middleware | `fastapi-x402` library handles it | Must implement `X-Payment` header verification manually |
| SSL/TLS | Railway provides HTTPS automatically | nginx + local cert (or Cloudflare tunnel if public access needed) |
| Uptime | Railway manages process lifecycle | macOS launchd plist required; home server power/network dependency |
| Availability | Public internet URL | LAN-only at `10.0.0.2` — not reachable from outside home network without tunnel |
| Deployment | `git push` or Railway CLI | `ssh 10.0.0.2 + git pull + restart service` |
| Cold start | Yes (Hobby tier) | No — process stays warm via launchd |
| Compute cost | Per-use billing | $0 marginal — hardware already owned |

**Key difference — x402 header verification:**

Railway services use `fastapi-x402` which handles the full 402 → payment → verification cycle. On the home server, this must be implemented manually:

```python
# x402_middleware.py — manual payment header verification
from fastapi import Request, HTTPException
import httpx

FACILITATOR_URL = "https://x402.org/facilitator"
WALLET_ADDRESS = "0x6b21227Ca9Bb3590BB62ff60BA0EFbBf9Ba22ACC"
PRICE_USDC = "10000"  # 0.01 USDC in 6-decimal units

async def verify_x402_payment(request: Request):
    payment_header = request.headers.get("X-Payment")
    if not payment_header:
        raise HTTPException(
            status_code=402,
            headers={
                "X-Payment-Required": f'{{"price":"{PRICE_USDC}","token":"USDC","network":"base","address":"{WALLET_ADDRESS}"}}'
            }
        )
    # Verify payment with x402 facilitator
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FACILITATOR_URL}/verify",
            json={"payment": payment_header, "amount": PRICE_USDC, "address": WALLET_ADDRESS}
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=402, detail="Payment verification failed")

@app.post("/transcribe")
async def transcribe(request: Request, audio_url: str):
    await verify_x402_payment(request)
    # ... MLX Whisper call ...
```

**nginx config for transcription (new server block):**

```nginx
# /etc/nginx/sites-available/x402-transcription
server {
    listen 8889;
    server_name 10.0.0.2;

    location / {
        proxy_pass http://127.0.0.1:8889;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # Transcription can be slow — generous timeout
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
```

Note: The brand site is already on port 8888. Transcription uses port 8889. The MCP server calls `http://10.0.0.2:8889` directly — this is fine because the MCP server runs on the same LAN.

**launchd plist for process persistence:**

```xml
<!-- ~/Library/LaunchAgents/com.x402.transcription.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" ...>
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.x402.transcription</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/uvicorn</string>
        <string>main:app</string>
        <string>--host</string><string>127.0.0.1</string>
        <string>--port</string><string>8889</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/jameswisdom/projects/x402-transcription-api</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/x402-transcription.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/x402-transcription-error.log</string>
</dict>
</plist>
```

### Pattern 3: MCP Tool Count Per API

**What:** Each new API gets 1–2 MCP tools: one for the primary action, optionally one for metadata/info about the service.

**Decision per API:**

| API | Tool(s) | Rationale |
|-----|---------|-----------|
| Web Scraping | `x402_scrape` (1 tool) | Single operation: URL → content. Params cover all extraction modes. |
| Email Sending | `x402_email_send` (1 tool) | Single operation: compose + send. No secondary tool needed. |
| Web Search | `x402_search` (1 tool) | Single operation: query → results. Count (N) is a param. |
| File Conversion | `x402_convert_file` (1 tool) | Single operation: file URL + target format → converted file. Format pair covers all conversions. |
| Audio Transcription | `x402_transcribe` (1 tool) | Single operation: audio URL → transcript. Language is optional param. |

Total: 5 new tools. MCP server grows from 6 to 11 tools.

The `x402_network_info` tool (already exists) will be updated to include the 5 new APIs in its health check output — this is a modification, not a new tool.

---

## Data Flow

### Standard Request Flow (Railway APIs, paid mode)

```
MCP Client calls x402_scrape({ url: "https://example.com" })
    │
src/index.ts tool handler
    │  PRIVATE_KEY present → usePaid = true
    │
apiGet(base, "/scrape?url=...", usePayment=true)
    │
getPaidFetch() → x402-fetch wraps native fetch with payment logic
    │
HTTP GET https://x402-scraping-api.up.railway.app/scrape?url=...
    │
Railway receives request, fastapi-x402 middleware checks for X-Payment header
    │  No header → 402 response with payment requirements
    │
x402-fetch intercepts 402, signs USDC payment, retries with X-Payment header
    │
Railway verifies payment, routes to handler, runs Playwright scrape
    │
JSON response → x402-fetch → apiGet → textResult → MCP client
```

### Standard Request Flow (Railway APIs, free test mode)

```
MCP Client calls x402_scrape({ url: "https://example.com" })
    │
src/index.ts — PRIVATE_KEY absent → usePaid = false
    │
apiGet(base, "/test/scrape?url=...", usePayment=false)
    │
HTTP GET https://x402-scraping-api.up.railway.app/test/scrape?url=...
    │  No middleware — test endpoint bypasses payment
    │  Hardcoded domain allowlist enforced in route handler
    │
JSON response → textResult → MCP client
```

### Transcription Request Flow (home server, paid mode)

```
MCP Client calls x402_transcribe({ audio_url: "https://..." })
    │
src/index.ts — usePaid = true
    │
apiPost("http://10.0.0.2:8889", "/transcribe", { url: ... }, true)
    │
x402-fetch → HTTP POST http://10.0.0.2:8889/transcribe
    │
nginx reverse proxy → uvicorn at 127.0.0.1:8889
    │
FastAPI — custom x402 middleware checks X-Payment header
    │  No header → 402 with payment requirements
    │
x402-fetch signs payment, retries
    │
FastAPI verifies payment via x402 facilitator API
    │
MLX Whisper: download audio URL → transcribe → JSON response
    │  (can take 5–60s depending on audio length)
    │
nginx → x402-fetch → apiPost → textResult → MCP client
```

### Key Data Flow Differences: Railway vs Home Server

| Step | Railway | Home Server |
|------|---------|-------------|
| x402 enforcement | `fastapi-x402` library (zero code) | Hand-rolled middleware in `x402_middleware.py` |
| SSL termination | Railway provides HTTPS | nginx on LAN — HTTP only (MCP server on same LAN, acceptable) |
| Process management | Railway platform | macOS launchd |
| Deployment | `git push` to Railway | SSH + git pull + `launchctl kickstart` |
| Availability to MCP server | Always (public URL) | Only when home server is on and accessible |
| URL in `src/index.ts` APIS dict | `https://...up.railway.app` | `http://10.0.0.2:8889` |

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (1 dev, personal use, LAN) | All services appropriate — Railway for 4 APIs, home server for transcription |
| Public launch (external agents calling APIs) | Transcription service is LAN-only — need Cloudflare Tunnel or ngrok to expose home server; or migrate to Railway with Whisper.cpp or Groq Whisper API |
| High traffic (100+ requests/day) | Railway services handle this automatically. Transcription: MLX Whisper is CPU-bound, sequential — queue system needed if concurrent requests arrive |
| Multiple developers | No change to Railway services. Home server transcription is the single point of fragility — document the dependency explicitly |

### Scaling Priorities

1. **First bottleneck:** Transcription is unavailable when home server is down, rebooting, or on a different network. Railway APIs are unaffected. Mitigation: launchd KeepAlive handles normal reboots. For v1.1 (personal use), this is acceptable — document clearly.
2. **Second bottleneck:** `src/index.ts` monolith at 11+ tools approaches 600 lines. Extract to `src/tools/` modules after v1.1 ships — this is a refactor, not a feature.

---

## Anti-Patterns

### Anti-Pattern 1: One Railway Service for All 4 New APIs

**What people do:** Bundle scraping, email, search, and file conversion into a single FastAPI service to minimize Railway projects.

**Why it's wrong:** Different dependency footprints (Playwright is huge, Resend is tiny), different scaling needs, different Railway environment configs. One slow deploy or broken dependency in one API takes down all four. Rollback becomes impossible if the services are coupled. Railway Hobby tier allows multiple projects — there is no cost reason to bundle.

**Do this instead:** One Railway service per API. Each deploys independently. Each has its own `requirements.txt` — Playwright's Chromium install doesn't bleed into the email sender's minimal footprint.

### Anti-Pattern 2: Using fastapi-x402 on the Home Server Without Verifying It Works on macOS

**What people do:** Copy the Railway pattern exactly — `pip install fastapi-x402`, add middleware — and assume it works on macOS Monterey x86_64 the same way it works on Railway's Linux containers.

**Why it's wrong:** `fastapi-x402` may have Linux-specific dependencies or expect Railway's environment variables (PORT, etc.). The library hasn't been validated on macOS. More importantly, the home server's payment verification doesn't need to be Railway-compatible — it just needs to correctly implement the x402 protocol spec.

**Do this instead:** Implement the x402 middleware manually on the home server using `httpx` to call the x402 facilitator API for payment verification. This is ~30 lines of code and has zero platform dependencies. Test it against the MCP server locally before declaring it done.

### Anti-Pattern 3: Pointing MCP Server at Home Server IP for Railway Services

**What people do:** Set `baseUrl` for scraping/email/search/conversion to `http://10.0.0.2:XXXX` during dev, then forget to update before shipping.

**Why it's wrong:** The published npm package (`x402-mcp-server`) will be installed by others via `npx`. Their MCP server will try to call `http://10.0.0.2` — their LAN, not the developer's — and fail with a connection refused error.

**Do this instead:** Railway services always get their production Railway URL in `src/index.ts`. Only the transcription service legitimately lives at `http://10.0.0.2:8889` — and the ARCHITECTURE doc should note this is a personal-use constraint (external users can't reach the home server).

### Anti-Pattern 4: Free Test Endpoint Allows Arbitrary URLs

**What people do:** Build the free test endpoint as a mirror of the paid endpoint but without payment enforcement — any URL allowed.

**Why it's wrong:** Free endpoints become abuse vectors. If scraping, transcription, or search accept any URL for free, the service will be scraped by bots and costs (Railway compute, Resend API calls if any leak through) will increase. The free tier is specifically for developer evaluation.

**Do this instead:** Free endpoints enforce a hardcoded allowlist: `example.com`, `example.org`, `httpbin.org` for URL-based tools. For email, the free endpoint sends only to a hardcoded test inbox (not user-specified `to` address). For search, the free endpoint returns hardcoded fixture data.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Railway (x4 new services) | Python FastAPI + fastapi-x402, deploy via Railway CLI or git push | Proven pattern from screenshot/PDF/sentiment services — replicate exactly |
| Resend API | Python `resend` SDK in email service | API key in Railway env var `RESEND_API_KEY` — never in MCP server |
| Web Search Backend (TBD) | HTTP API call from search service | SerpAPI / Brave / Tavily — research during search API build; key in Railway env var |
| MLX Whisper | Python `mlx_whisper` library call in transcription service | Already installed on home Mac (`whisper-large-v3-mlx` model per MEMORY.md) — no install needed |
| x402 Facilitator API | HTTP call from home server transcription middleware | `https://x402.org/facilitator/verify` — payment verification |
| macOS launchd | plist file in `~/Library/LaunchAgents/` | Keeps transcription uvicorn process alive after reboots |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| MCP server ↔ Railway APIs | HTTP via x402-fetch, URLs in `APIS` dict | Add 4 new entries to APIS dict in `src/index.ts` |
| MCP server ↔ Home transcription | HTTP via x402-fetch, `http://10.0.0.2:8889` | Same x402-fetch call — the library doesn't care if the URL is Railway or home server |
| nginx ↔ uvicorn (home server) | Local proxy on 127.0.0.1:8889 | nginx forwards to local process; not exposed directly |
| Home transcription ↔ x402 facilitator | Outbound HTTPS from home server | Requires internet access from home server; verify firewall rules |
| `x402_network_info` tool ↔ all APIs | Parallel `checkHealth()` calls | Update `APIS` dict to include new services; health checks run on each `x402_network_info` call |

---

## Build Order

Build order respects two constraints: (1) Railway services are independent of each other and can be built in parallel or any order, (2) the MCP server update (`src/index.ts`) requires each service's Railway URL, so it must happen after each service is deployed.

**Recommended sequence:**

1. **Scraping API** — start here because it has the most interesting complexity (Playwright headless in Railway container — verify Playwright Chromium install works in Railway's Docker environment before committing to it). Free test endpoint with allowlisted domains. Deploy to Railway, get URL.

2. **File Conversion API** — second because it's the most self-contained (no third-party API keys needed, just Python conversion libs: `weasyprint` for html-to-pdf, `Pillow` for image resize, `pandas` for csv-to-json). Deploy to Railway, get URL.

3. **Search API** — third because it needs a search backend decision first. Research SerpAPI vs Brave vs Tavily during the file conversion build to avoid blocking. Once decided, build is straightforward (thin wrapper). Deploy to Railway, get URL.

4. **Email API** — fourth because it requires a Resend account and API key setup. Simple to build (Resend has a clean Python SDK). The free test endpoint sends to a hardcoded test address. Deploy to Railway, get URL.

5. **Transcription API (home server)** — last among backends because it has the most infrastructure work (custom x402 middleware, nginx config, launchd plist). MLX Whisper is already installed, which eliminates the hardest dependency. Do this after Railway services validate that x402 middleware patterns are working end-to-end.

6. **MCP server update (`src/index.ts`)** — after all 5 service URLs are known. Add 5 entries to `APIS` dict, 5 `server.tool()` blocks. Update `x402_network_info` health check logic to include new services. Bump version to `1.1.0`.

7. **Integration test** — test all 11 tools in both free and paid mode before `npm publish`.

8. **`npm publish 1.1.0`** — after integration test passes.

**Rationale for ordering scraping first:** Playwright in a Railway container requires Chromium installation at build time. Railway uses Nixpacks to detect Python apps. Chromium install in Nixpacks requires a `nixpacks.toml` config (`pkgs = ["chromium", "playwright"]`) — this is the highest-risk unknown in the batch. Proving it works first means Railway compatibility is validated before the other (simpler) services are built.

**Rationale for transcription last:** The home server pattern has more infrastructure steps (nginx, launchd, custom middleware) than any single Railway service. Building it last means x402 middleware patterns are already understood from the Railway implementations, reducing implementation uncertainty.

---

## Sources

- Existing `src/index.ts`: established APIS dict pattern, apiGet/apiPost helpers, getPaidFetch lazy init, Zod param validation conventions
- Existing Railway services (screenshot, PDF, sentiment): baseline for FastAPI + fastapi-x402 structure
- PROJECT.md v1.1 requirements: 5 API targets, Railway vs home server hosting decision, MLX Whisper on home server confirmed
- MEMORY.md: `whisper-large-v3-mlx` model confirmed installed on home Mac; nginx already running at port 8888 on 10.0.0.2
- PITFALLS.md (v1.0): Zod `.url()` and `.regex()` required on all input params — apply same discipline to v1.1 tools
- x402 protocol: 402 response header format, X-Payment header structure, facilitator verification endpoint

---
*Architecture research for: v1.1 Universal Utility APIs — 5 new backends integrating with existing x402 MCP server*
*Researched: 2026-03-12*
