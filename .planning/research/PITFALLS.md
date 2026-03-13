# Pitfalls Research

**Domain:** Universal Utility APIs v1.1 — Web Scraping, Email Sending, Web Search, File Conversion, Audio Transcription
**Researched:** 2026-03-12
**Confidence:** HIGH

---

## Critical Pitfalls

### Pitfall 1: MLX Whisper Requires Apple Silicon — Will Not Run on Intel x86_64

**What goes wrong:**
The home server at 10.0.0.2 runs macOS Monterey on an Intel x86_64 processor. MLX is Apple's machine learning framework that **only runs on Apple Silicon (M1/M2/M3)**. `pip install mlx` will fail with a platform error on Intel. Any service built around `mlx_whisper` or `mlx-whisper` will fail to start on the home server, producing a confusing Python import error rather than a clear "wrong CPU architecture" message.

**Why it happens:**
MLX is compiled against Apple Silicon's unified memory architecture and uses Metal (Apple's GPU API), neither of which exist on Intel Macs. The PyPI package has platform markers that exclude x86_64 darwin, but error messages from failed installs don't always make the architecture incompatibility obvious. Developers who use MLX Whisper on an M-series MacBook assume their home server can run the same stack.

**How to avoid:**
Use `faster-whisper` (CTranslate2-based) or `openai-whisper` instead. `faster-whisper` is the correct production choice for x86_64:
- `pip install faster-whisper`
- 4x faster than original Whisper on CPU via CTranslate2 quantization
- Same model names: `base`, `small`, `medium`, `large-v3`
- Same API shape: `model.transcribe(audio_path)`
- No GPU required — CPU inference works well for the `small` and `medium` models
- Docker image available if containerization is needed later

Verify before any implementation work: `uname -m` on the home server must return `x86_64`; if so, install `faster-whisper`, not anything `mlx`.

**Warning signs:**
- `pip install mlx` or `pip install mlx-whisper` in any requirements.txt or setup script
- `import mlx` anywhere in the transcription service code
- Any service documentation referencing Apple Silicon acceleration for the home server

**Phase to address:**
Phase 1 (transcription backend setup) — before any code is written. The first step must be confirming the home server's architecture and selecting the correct Whisper variant.

---

### Pitfall 2: Playwright in Railway Containers — Missing System Dependencies Cause Silent Chromium Crash

**What goes wrong:**
Playwright's bundled Chromium requires specific system libraries (glibc, libnss, libxss, libgbm, etc.) that are not present in minimal Railway Docker images (based on Debian slim or Alpine). The install step `playwright install chromium` succeeds because it downloads the browser binary, but the binary crashes on launch with `error while loading shared libraries` or just `spawn ENOENT`. The FastAPI endpoint returns a 500 with a cryptic subprocess error, not a Chromium-missing error.

**Why it happens:**
`playwright install chromium` only downloads the browser binary — it does not install system dependencies. The separate command `playwright install-deps chromium` installs system packages via apt, but this requires root and a full Debian (not Alpine) base image. Developers who test on their laptop (where Chromium runs fine due to an existing full desktop environment) don't encounter the missing library issue until the Railway deploy.

**How to avoid:**
Use the official Playwright Docker base image as the Railway service's base image:
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy
```
This includes all Chromium system dependencies pre-installed. Alternatively, use `debian:bookworm` or `ubuntu:22.04` as the base (not Alpine or slim variants) and run `playwright install-deps chromium` in the Dockerfile. Never use Alpine for a Playwright container — musl libc is incompatible with Chromium's glibc requirement.

In `railway.toml` or the Railway build config, set `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` if using the official image; the browsers are already installed there.

**Warning signs:**
- Dockerfile uses `python:3.11-slim` or any Alpine base image
- `playwright install chromium` in the Dockerfile but no `playwright install-deps` or base image swap
- Railway build logs show Playwright install succeeding but runtime shows `ENOENT` or `SIGKILL` on browser launch
- Local tests pass but Railway deployment returns 500 on scraping requests

**Phase to address:**
Phase 1 (web scraping backend setup) — Dockerfile must be correct before any Railway deploy. Test the container locally with `docker build && docker run` before pushing to Railway.

---

### Pitfall 3: Playwright in Railway — Memory Exhaustion at Default Container Size

**What goes wrong:**
Each Playwright browser instance requires approximately 200–400MB of RAM. Railway's starter tier provides 512MB. A FastAPI web scraping service that launches a new Playwright browser per request will run out of memory after 2–3 concurrent requests. Railway kills the container with OOM (Out of Memory), which appears as a 502 or instant connection reset — no error message from the application itself.

**Why it happens:**
Developers benchmark locally where RAM is plentiful. The containerized environment's tight memory ceiling doesn't manifest until concurrent requests hit the service. Playwright's Chromium process is much heavier than it appears — even a "headless" browser loads the full Blink rendering engine, V8, and network stack.

**How to avoid:**
Two mitigations, both required:
1. **Use a persistent browser pool, not per-request browser launches.** Launch one Chromium instance at service startup with `playwright.chromium.launch()`, and reuse it across requests. Create a new page per request (`browser.new_page()`), scrape, then close the page — not the browser. This keeps memory at ~300MB constant instead of linearly increasing with requests.
2. **Set Railway service memory to at least 1GB.** The starter plan is insufficient for production. This is a cost decision, but 512MB will OOM under any realistic concurrent load.

```python
# At startup (lifespan event in FastAPI)
browser = await playwright.chromium.launch(headless=True)

# Per request
page = await browser.new_page()
await page.goto(url)
content = await page.content()
await page.close()  # close page, not browser
```

**Warning signs:**
- `browser = await playwright.chromium.launch()` inside a request handler (not a startup event)
- Railway service configured with 512MB memory
- Intermittent 502 errors during load testing
- Railway logs show container restart without explicit error message

**Phase to address:**
Phase 1 (web scraping backend) — browser lifecycle architecture must be correct from the first commit.

---

### Pitfall 4: Playwright Anti-Bot Blocks — Cloudflare and Similar Systems Detect Headless Chromium

**What goes wrong:**
Roughly 30–40% of production websites use Cloudflare or similar anti-bot systems that detect headless Chromium via browser fingerprinting. The detection checks include: `navigator.webdriver` being true, missing Chrome extensions, headless window dimensions, and specific timing patterns in JavaScript execution. When detected, the server returns a Cloudflare challenge page instead of the actual content — Playwright receives 200 OK with a challenge HTML body, not an error. The scraping endpoint returns "content" that is actually a bot challenge page.

**Why it happens:**
Playwright's default `headless=True` mode does not suppress the `navigator.webdriver` flag or other headless signals. This is intentional — Playwright prioritizes correctness over stealth. The service appears to work during development (testing against cooperative test URLs) but fails against real-world targets.

**How to avoid:**
Two approaches:
1. **`stealth` mode via `playwright-stealth` or equivalent.** In Python: `pip install playwright-stealth`, then `await stealth_async(page)` after `browser.new_page()`. This patches the most common detection vectors.
2. **Document the limitation honestly.** The API description should state: "Works on most sites. Sites with advanced bot protection (Cloudflare Enterprise, Akamai) may return challenge pages instead of content." Set a `blocked` field in the response JSON when detecting challenge pages (check for `cf-mitigated` header or `challenge-platform` in response body).

Do not promise 100% scraping success — it is not achievable without more expensive residential proxy infrastructure.

**Warning signs:**
- Response body contains `"Just a moment..."` or `"Checking your browser"` (Cloudflare challenge phrases)
- Response body is under 2KB for a page that should have substantial content
- HTTP status is 200 but response contains `<title>Attention Required!</title>` or similar
- Test URLs used during development are all cooperative sites (GitHub, Wikipedia) with no Cloudflare protection

**Phase to address:**
Phase 1 (web scraping backend) — stealth mode and challenge detection must be in the initial implementation. The API contract must document success rate limitations.

---

### Pitfall 5: Resend From-Address Deliverability — Custom `from:` Requires Domain Ownership Proof

**What goes wrong:**
Resend allows sending email, but only from domains whose SPF and DKIM records you control. Sending from an arbitrary `from:` address (e.g., a user-supplied `from` parameter) without DNS verification will fail with a 422 or result in the email landing directly in spam. More critically: if the API allows a caller to specify any `from:` address, it becomes an open relay for domain spoofing — any agent can impersonate any organization.

**Why it happens:**
Developers test Resend with their own verified domain and it works. When they design the API to accept a caller-supplied `from:` parameter (to make it "flexible"), they don't realize Resend validates the from-domain against the account's verified domains list. The service either rejects the send or, if using a shared Resend domain, silently limits deliverability.

**How to avoid:**
Two options:
1. **Fixed sender, caller-supplied recipient:** The API only accepts `to`, `subject`, `body`. The `from:` is hardcoded to a verified domain you own (e.g., `noreply@x402.network` or `api@yourverifieddomain.com`). This is simple, deliverable, and non-spoofable. The limitation is that recipient replies go to your domain.
2. **If custom from-domain is needed:** Require the caller to supply a Resend API key tied to their own account and verified domain — but this fundamentally changes the service from "pay-per-use" to "API key proxy," which undermines the x402 model.

**Recommendation: Option 1.** One verified sender domain. The from-domain registration in Resend requires adding TXT/CNAME records — do this before writing any API code and verify with Resend's domain verification UI.

DNS records needed (Resend will provide the exact values):
- SPF: `v=spf1 include:amazonses.com ~all` (Resend uses SES)
- DKIM: CNAME records pointing to Resend's signing infrastructure
- DMARC: `v=DMARC1; p=quarantine; rua=mailto:postmaster@yourdomain.com`

**Warning signs:**
- The API schema includes a `from` parameter that accepts arbitrary email addresses
- No domain verified in the Resend dashboard before writing the FastAPI endpoint
- Resend returns 422 "from address not verified" during first test send
- Test emails arrive in spam folder with DMARC fail in headers

**Phase to address:**
Phase 1 (email backend setup) — domain DNS records must be configured and verified in Resend before writing any API code. This has a real-world DNS propagation delay (up to 48 hours).

---

### Pitfall 6: Resend Abuse Surface — The Email API Becomes a Spam Cannon

**What goes wrong:**
A pay-per-use email sending API with no recipient validation or rate limiting is an extremely attractive target for spam operators. Even at $0.05 per send, bulk spam becomes cheap if the attacker's cost for sending 10,000 emails is $500 (cheaper than most email services). Once the Resend account gets flagged for abuse, the account is suspended and all email from the verified domain is blacklisted.

**Why it happens:**
The x402 micropayment wall provides economic friction but not abuse prevention. Spam operators routinely fund wallets with small amounts and probe APIs for abuse vectors. The API accepts a `to` address and body from the caller — if neither is validated or limited, it's a spam service.

**How to avoid:**
Mandatory restrictions:
1. **Recipient domain allowlist or content policy.** Either restrict `to` addresses to verified recipients (practical for specific use cases) or implement body length limits and reject known spam indicators.
2. **Per-sender rate limiting at the FastAPI layer.** Maximum N emails per wallet address per hour. Store counts in Redis or a simple in-memory dict (acceptable for low volume). Suggested limit: 10 sends per wallet per 24 hours.
3. **No HTML body.** Accept only plain text or simple Markdown in the body field. Reject or strip any HTML, which is the primary vector for phishing content.
4. **Subject and body length limits.** Subject: 200 chars max. Body: 5000 chars max. Zod validation enforces this on the MCP server side; FastAPI enforces it on the backend.
5. **Log all sends.** Each send should log: wallet address, `to` domain (not full address), subject hash, timestamp. Do not log full `to` address or body — PII concern.

**Warning signs:**
- No rate limiting logic in the FastAPI email endpoint
- Body field accepts HTML or has no length limit
- No logging of send events
- The API description markets "bulk email" as a use case

**Phase to address:**
Phase 1 (email backend setup) — abuse controls must be in the initial implementation, not added after reports. Resend account suspension is a non-recoverable situation for the verified domain's reputation.

---

### Pitfall 7: Web Search API Cost Spikes — Uncapped Per-Query Costs at Search Provider Level

**What goes wrong:**
Search APIs (SerpAPI, Brave, Tavily, etc.) charge per query at the provider level. If the x402 API wraps the search provider without its own spend caps, a single agent in a loop making hundreds of search queries in an hour can exhaust the monthly API budget in minutes. SerpAPI bills $50–$75 for 5,000 searches. An agent loop making 100 searches per minute hits that limit in under an hour.

**Why it happens:**
The x402 service charges the calling agent per search (revenue), but the search provider charges the service per search (cost). If `cost_per_search_to_agent > cost_per_search_from_provider` then the service is profitable per call — but there's no cap on total volume. An agent bug, runaway loop, or intentional abuse can drain the entire monthly search provider budget before billing resets.

**How to avoid:**
1. **Hard monthly spend cap at the provider level.** All major search APIs have monthly credit limits or billing alerts — enable these at the provider dashboard (e.g., SerpAPI credit limit, Brave Search API hard limit). Set the limit to 110% of expected budget, not unlimited.
2. **Per-wallet daily query limit.** Same pattern as email: max N searches per wallet address per 24 hours. Suggested limit: 50–100 queries per wallet per day for the free test endpoint; no limit (or higher limit) for paid callers.
3. **Choose a provider with predictable per-query pricing.** Avoid providers that charge per API call with variable pricing based on query complexity. Brave Search API and Tavily both have flat per-query pricing and free tiers appropriate for development.

**Warning signs:**
- Search provider billing alert not configured
- No per-caller rate limiting in the FastAPI search endpoint
- Provider dashboard shows no spending cap
- Monthly search provider bill exceeds the month's x402 revenue from search calls

**Phase to address:**
Phase 1 (search backend setup) — billing alerts and per-caller rate limits must be configured before the endpoint goes live, not after the first billing cycle.

---

### Pitfall 8: LibreOffice in Railway Containers — 500MB+ Image Size and 10+ Second Cold Start

**What goes wrong:**
LibreOffice is required for reliable document conversion (DOCX → PDF, ODT → PDF). The LibreOffice package on Debian/Ubuntu is approximately 500MB installed. Adding it to a Railway Docker image inflates the image size to 700MB–1GB+ (base image + LibreOffice + Python + FastAPI). Railway has a 1GB image size recommendation; larger images cause slow cold starts (30+ seconds) and may hit hard limits on some plans. More critically, LibreOffice itself takes 5–8 seconds to start in headless mode — if launched per-request, every file conversion request has an 8-second minimum latency before any work happens.

**Why it happens:**
LibreOffice is the industry standard for server-side document conversion and works reliably for complex .docx files. Developers install it on a local machine where the 500MB footprint is irrelevant and headless startup time isn't noticed because they run it interactively. The container performance profile is entirely different.

**How to avoid:**
Two mitigations:

1. **Pre-warm LibreOffice at container startup.** Run a dummy conversion in the FastAPI `lifespan` startup event to force LibreOffice to load its JVM/module cache. This moves the 8-second startup cost to container startup (not first request):
```python
import subprocess
# In lifespan startup:
subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", "/tmp", "/dev/null"],
               capture_output=True)
```

2. **Consider lighter alternatives for simple conversions.** For HTML → PDF, use `weasyprint` (pure Python, ~50MB) instead of LibreOffice. For DOCX → PDF specifically, LibreOffice is genuinely the best option — but document this cost clearly. For CSV → JSON, no LibreOffice needed at all — use Python's built-in `csv` module.

3. **Use a multi-stage Docker build to minimize the final image size.** LibreOffice installation produces many locale files and documentation that can be removed:
```dockerfile
RUN apt-get install -y libreoffice --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/lib/libreoffice/share/gallery \
    && rm -rf /usr/lib/libreoffice/share/template
```
This can reduce the LibreOffice footprint to ~350MB.

**Warning signs:**
- `libreoffice --headless` called in a subprocess inside a request handler (not pre-warmed)
- Railway image size exceeds 800MB (visible in Railway build logs)
- First-request latency for file conversion exceeds 15 seconds
- Railway service shows frequent cold starts due to large image

**Phase to address:**
Phase 1 (file conversion backend setup) — Dockerfile and startup pre-warming must be designed before the first Railway deploy.

---

### Pitfall 9: File Conversion — Temporary File Accumulation in Container Filesystem

**What goes wrong:**
File conversion requires writing input files and output files to disk. If these temp files are not cleaned up, a Railway container's ephemeral filesystem fills up over time. Railway containers have a 512MB–1GB filesystem limit depending on the plan. A conversion service that receives 100 files per day without cleanup will exhaust the filesystem in hours depending on file sizes, causing all subsequent writes (and thus all conversions) to fail with `OSError: [Errno 28] No space left on device`.

**Why it happens:**
Developers use `tempfile.NamedTemporaryFile()` without ensuring cleanup on both success and failure paths. If a conversion fails mid-process (e.g., LibreOffice crashes), the `finally` block or cleanup code may not run. Over time, failed requests accumulate temp files that are never deleted.

**How to avoid:**
Always use `tempfile.TemporaryDirectory()` as a context manager — it guarantees cleanup even on exception:
```python
import tempfile
import contextlib

@contextlib.asynccontextmanager
async def temp_workdir():
    with tempfile.TemporaryDirectory(prefix="x402-convert-") as tmpdir:
        yield tmpdir
# Files in tmpdir are deleted when the context exits, on any exit path
```
Set a maximum input file size (e.g., 10MB) enforced before writing to disk. Log filesystem usage in the health check endpoint: `shutil.disk_usage("/tmp")`.

**Warning signs:**
- Temp files created with `open("/tmp/filename", "wb")` without guaranteed cleanup
- No try/finally or context manager around file operations
- Health check endpoint does not include disk usage
- Container filesystem usage growing monotonically (visible in Railway metrics)

**Phase to address:**
Phase 1 (file conversion backend) — cleanup pattern must be in the initial implementation.

---

### Pitfall 10: Input File URL Fetch — SSRF Against Internal Railway Network

**What goes wrong:**
The file conversion and audio transcription APIs accept a URL pointing to the input file. If the URL is user-supplied without validation, an agent can supply internal Railway URLs (e.g., `http://10.0.0.1/internal-api`, `http://metadata.internal/computeMetadata/v1/`) to probe Railway's internal network or access cloud metadata endpoints. On Railway, the internal metadata service exposes environment variables including API keys.

**Why it happens:**
The pattern "fetch a file from a URL" looks identical for legitimate URLs and SSRF payloads. Developers validate that the URL is "a valid URL" (using Python's `urllib.parse.urlparse`) without checking that it resolves to a public IP, not an internal one.

**How to avoid:**
Before fetching any user-supplied URL:
1. Resolve the hostname to an IP address
2. Reject any RFC 1918 address (10.x.x.x, 172.16.x.x–172.31.x.x, 192.168.x.x) and loopback (127.x.x.x)
3. Reject non-http/https schemes
4. Set a download timeout and file size limit

```python
import ipaddress, socket, urllib.parse

def is_safe_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    try:
        ip = socket.gethostbyname(parsed.hostname)
        addr = ipaddress.ip_address(ip)
        return not (addr.is_private or addr.is_loopback or addr.is_link_local)
    except Exception:
        return False
```

This validation must happen on the **FastAPI backend**, not just the MCP server's Zod validation — the backend is the last line of defense.

**Warning signs:**
- `requests.get(user_url)` without IP validation on the backend
- Zod `.url()` validation on the MCP server side only (necessary but insufficient — `.url()` accepts `http://10.0.0.1/`)
- Any endpoint that fetches a user-supplied URL without a timeout
- No file size limit on downloads

**Phase to address:**
Phase 1 (file conversion + transcription backends) — SSRF prevention must be in the initial implementation. Both the file conversion and transcription APIs share this attack surface.

---

### Pitfall 11: Playwright Timeout Cascades — Long-Running Scrapes Block FastAPI Workers

**What goes wrong:**
Playwright's default `goto()` timeout is 30 seconds. On a slow or broken target site, one scraping request holds a FastAPI async worker for 30 seconds. If multiple requests arrive during that window, the async event loop is not blocked (FastAPI uses asyncio) — but the shared Playwright browser instance is occupied. If all concurrent requests hit slow sites simultaneously, request queue depth grows and Railway's request timeout (typically 30s at the load balancer) kills requests before Playwright can finish, producing empty responses that look like successful returns.

**Why it happens:**
FastAPI's async model makes it appear that concurrent requests are handled independently. They are — but they share the single `browser` instance (Pitfall 3's pool). A long `page.goto()` occupies the page until timeout; other requests are queued waiting for a free page slot if only one browser is available.

**How to avoid:**
1. **Reduce Playwright timeouts to match the service's SLA.** The x402 scraping service should respond in under 10 seconds. Set `page.set_default_timeout(8000)` (8 seconds) so Playwright gives up before Railway's load balancer does.
2. **Set a page pool limit.** Allow max N concurrent pages (e.g., 3). Return a 503 "service busy" if the pool is exhausted. This is explicit about capacity rather than letting requests silently queue.
3. **Return a partial result on timeout.** If `goto()` times out but the page has loaded some content (from the initial response), return what was captured rather than an error.

**Warning signs:**
- No explicit timeout set on `page.goto()` or `page.set_default_timeout()`
- No concurrency limit on simultaneous page instances
- p99 response time in Railway metrics showing clustering at exactly 30 seconds (the default Playwright timeout)

**Phase to address:**
Phase 1 (web scraping backend) — timeout and concurrency limits must be in the initial implementation.

---

### Pitfall 12: Audio Transcription — Large Audio File Handling on Home Server

**What goes wrong:**
The transcription API accepts an audio URL and returns a transcript. If there is no file size limit, callers can supply multi-hour audio files (podcast archives, meeting recordings) that take 10–60 minutes to transcribe on `faster-whisper` with CPU inference. The home server (10.0.0.2) has no request timeout if served directly via FastAPI, causing the MCP tool call to hang indefinitely. The MCP client times out and the caller has no way to retrieve the result.

**Why it happens:**
The "stateless, sub-$0.10" positioning for x402 APIs implies synchronous request-response. Audio transcription is fundamentally not a low-latency operation for long files. Developers test with 30-second voice memos and it works fine; they don't test with 2-hour podcasts. The architecture mismatch surfaces only in production with real user inputs.

**How to avoid:**
Two constraints that must both be enforced:
1. **Hard file size limit: 25MB.** This is Whisper's own practical limit for quality results. Above 25MB, longer audio needs chunking, which adds complexity. Reject at the URL-fetch stage before downloading: check `Content-Length` header, abort if > 25MB.
2. **Hard duration limit: 10 minutes.** After downloading, use `ffprobe` to check audio duration before transcribing. Return a 413 "file too large" if duration exceeds 10 minutes.
3. **Set a server-side transcription timeout.** Run `faster-whisper` transcription in a subprocess with a timeout. If it exceeds 5 minutes (300s), kill the subprocess and return a 504.

```python
import subprocess, signal
# Run transcription with timeout
result = subprocess.run(
    ["python", "-m", "transcribe_worker", audio_path],
    timeout=300,  # 5 minute hard limit
    capture_output=True
)
```

**Warning signs:**
- No `Content-Length` check before downloading audio
- No `ffprobe` duration check before transcribing
- No subprocess timeout on the `faster-whisper` invocation
- The API description mentions "long audio files" as a use case without limits stated

**Phase to address:**
Phase 1 (transcription backend setup) — size and duration limits must be enforced from day one. The home server has no autoscaling and cannot be restarted mid-transcription without losing the work.

---

### Pitfall 13: Home Server Transcription — Network Accessibility and Firewall

**What goes wrong:**
The transcription API lives on the home server at 10.0.0.2, not Railway. Railway's other APIs are publicly accessible. The MCP server's TypeScript code calls the transcription endpoint at `http://10.0.0.2:PORT/transcribe`. This works when the MCP server runs on the same local network — but MCP clients (Claude Desktop on a developer's remote machine, or agents running in the cloud) cannot reach 10.0.0.2. The call fails immediately with `ECONNREFUSED` or a timeout.

**Why it happens:**
The existing screenshot and PDF APIs are on Railway (publicly accessible). The MLX/Whisper transcription was planned for the home server to avoid GPU rental costs. The assumption is that the MCP server always runs on the same local network as the home server. This assumption breaks as soon as anyone uses the MCP server from outside the local network.

**How to avoid:**
Two options:
1. **Expose the home server publicly.** Configure port forwarding on the home router for the transcription API port, and optionally set up a subdomain with dynamic DNS. This makes the transcription endpoint publicly accessible. Security risk: a public FastAPI endpoint on a home server is a target — ensure it runs with x402 payment validation (only paid requests are processed) and rate limiting.
2. **Host transcription on Railway with a Whisper Docker image (CPU-only).** Railway can run `faster-whisper` on CPU without GPU. This removes the local network dependency. The cost is Railway compute time for CPU inference — but at small volume, the free tier likely covers it. This is the cleaner architectural choice.

**Recommendation:** Start with option 1 (home server with port forwarding) for v1.1 since the hardware is already available. Document the network requirement clearly. Plan migration to Railway CPU inference if usage grows.

**Warning signs:**
- Hardcoded `http://10.0.0.2` URL in the MCP server's tool configuration
- No port forwarding configured on the home router for the transcription service port
- No public DNS name for the home server transcription endpoint
- Testing only from within the local network

**Phase to address:**
Phase 1 (transcription backend) — network accessibility must be confirmed before the MCP tool is wired up. The URL hardcoded in `src/index.ts` must be reachable from anywhere, not just the local network.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Single Playwright browser instance (no pool) | Simple code; avoids pool management complexity | First concurrent request blocks second; OOM if browser leaks | MVP with expected low concurrency — but document the limit |
| `faster-whisper` on CPU without GPU | No cloud GPU cost; uses existing hardware | 10x–20x slower than GPU inference; long audio files are impractical | Acceptable for v1.1 at low volume; plan GPU migration when transcription becomes a popular tool |
| LibreOffice for all doc conversions | One tool handles all formats | 500MB image, 8s cold start; overkill for simple conversions | Acceptable for v1.1; extract lightweight alternatives (weasyprint for HTML→PDF) in v1.2 |
| No async task queue for long operations | Synchronous request-response is simpler to build and test | Transcription and large file conversion exceed MCP client timeouts; callers get confusing errors | Never acceptable for operations > 30s — add a job ID + polling pattern or enforce strict size limits |
| Hardcoded verified sender email | No per-user domain setup; simple to implement | Replies go to your domain; can't be white-labeled; limits enterprise use cases | Acceptable for v1.1; this is the correct MVP approach |
| In-memory rate limiting (dict, not Redis) | No Redis dependency; simpler deploy | Rate limits reset on container restart; doesn't work across multiple Railway instances | Acceptable at single-instance scale; requires Redis if Railway scales to multiple instances |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Resend API | Setting `from:` to a domain you don't control | Configure DNS (SPF, DKIM, DMARC) for your verified sender domain before writing any code; use only that domain in `from:` |
| Resend API | Not handling Resend's rate limits (100 reqs/sec) | Add `X-RateLimit-*` header parsing; 429 responses from Resend should return a 503 (not 500) from the FastAPI endpoint |
| Playwright + Railway | `playwright install chromium` in Dockerfile without installing system deps | Use `mcr.microsoft.com/playwright/python:*-jammy` base image or run `playwright install-deps chromium` separately after installing Playwright |
| LibreOffice + Railway | Installing LibreOffice without `--no-install-recommends` | Add `--no-install-recommends` and remove locale/gallery files post-install to reduce image size by ~150MB |
| Search API (SerpAPI/Brave/Tavily) | No billing alert at the provider level | Set hard monthly spend cap in provider dashboard before first production request |
| faster-whisper on x86_64 | Using float16 model precision (GPU-only) | Use `compute_type="int8"` for CPU inference — float16 is GPU-only and will error on CPU; int8 is 4x faster on CPU than float32 |
| faster-whisper | Transcribing MP4/MKV video files directly | Run `ffmpeg -i input.mp4 -ac 1 -ar 16000 output.wav` first — Whisper works on 16kHz mono WAV; feeding video directly can produce poor results |
| Home server + nginx | Running FastAPI on port 8888 (already used by brand site) | Use a different port (e.g., 8889 or 9000) for the transcription FastAPI service; check `netstat -tlnp` before choosing a port |
| x402 payment validation | Bypassing payment check for "test" endpoints in production | Ensure test endpoints use the same FastAPI router but with `price=0`; never disable the payment middleware in production containers |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Per-request Playwright browser launch | p50 response time > 5s; OOM at 3+ concurrent users | Persistent browser at startup, per-request pages | Breaks at first concurrent request in a 512MB container |
| LibreOffice launched per request (not pre-warmed) | 8–10s latency on first request after cold start | Pre-warm in FastAPI lifespan startup event | Every cold start (Railway scales to zero after inactivity) |
| No page size limit on downloaded files | Container filesystem fills up; disk errors after N requests | Enforce 25MB limit on all URL-fetched inputs at download time | Breaks when any caller sends a large file — could be the first real request |
| Synchronous transcription with no timeout | MCP client times out; Railway request returns 504 | Subprocess timeout + file size/duration pre-check | Breaks on any audio file longer than ~5 minutes |
| Search API without per-caller rate limiting | Monthly search budget exhausted by one active agent | In-memory rate limit: N searches per wallet per day | Breaks the moment any agent starts looping on search |
| Resend without per-caller send limits | Resend account flagged for spam; entire domain blacklisted | In-memory rate limit: N sends per wallet per day | Breaks if any caller sends bulk email — could be the first day |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| User-supplied `from:` address in email API | Open relay for phishing; domain spoofing; Resend account suspension | Hardcode the `from:` to your verified domain only; never accept caller-supplied from-address |
| No SSRF protection on URL-fetch endpoints | Internal Railway network access; cloud metadata endpoint exfiltration | IP range check before any `requests.get(user_url)` — reject RFC 1918, loopback, link-local |
| LibreOffice processing untrusted documents | CVE exposure from malicious DOCX/ODT macros; file system access via embedded scripts | Run `libreoffice --headless --norestore --nofirststartwizard --noscripting` — the `--noscripting` flag disables macro execution |
| Transcription API accepting `file://` URIs | Local filesystem read on home server | Scheme validation: only `http://` and `https://` accepted in audio URL parameter; reject before download |
| Playwright scraping arbitrary URLs on Railway | Internal Railway metadata access via `http://metadata.internal/` | Same SSRF protection as file fetch endpoints — validate that the scrape target resolves to a public IP |
| Email body containing user-supplied HTML | Phishing content sent from your verified domain; Resend account suspension | Accept only plain text or Markdown in email body; strip or reject HTML entirely |
| Temporary files written with predictable names | File collision attacks if two concurrent requests use the same temp name | Use `tempfile.TemporaryDirectory()` which generates random names; never construct `/tmp/conversion-{user_id}` by hand |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Scraping API returns raw HTML instead of structured data | Agent receives 50KB of HTML and must parse it itself — this is what agents pay to avoid | Always return structured JSON: `{title, text, links[], tables[], metadata}` — Cheerio handles the extraction server-side |
| File conversion API returns base64-encoded file in JSON | Base64 inflates file size 33%; large files cause MCP transport issues on the stdio channel | Return a download URL or a presigned Railway storage URL; do not embed file bytes in JSON responses |
| Transcription API returns only the raw transcript string | Agent has no timing information; no speaker detection; no confidence scores | Return `{transcript, segments[{start, end, text}], language, duration}` — same shape as Whisper's native output |
| Search API returns raw search engine HTML | Defeats the purpose of paying for structured search results | Return `{results[{title, url, snippet}], query, result_count}` — parse at the server, not at the client |
| Email API has no confirmation in the response | Agent doesn't know if the email was delivered | Return `{message_id, status, to}` from Resend's API response — Resend provides a message ID for every accepted send |
| No `free_test` endpoint for new APIs | Developers can't try the API without funding a Base wallet | Every new API must have a free test endpoint (same pattern as existing screenshot/PDF/sentiment) |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Transcription on home server:** `faster-whisper` installed and serving — verify by running `uname -m` first; confirm it returns `x86_64`; confirm `import faster_whisper` works without error before wiring up the API
- [ ] **Playwright container:** Chromium launches without errors — verify by running `docker run <image> python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(); print('OK'); b.close()"` in the Railway image before deploying
- [ ] **Resend sender domain:** DNS records configured — verify by sending a test email and checking the received headers for `dkim=pass` and `spf=pass` in the `Authentication-Results` header; not just that the email arrived
- [ ] **SSRF protection:** URL validation in place — verify by calling the scraping/conversion/transcription endpoints with `url=http://192.168.1.1/` and confirming a 422 rejection, not a connection attempt
- [ ] **LibreOffice noscripting:** Macro execution disabled — verify the subprocess call includes `--noscripting` flag; test with a DOCX that contains a macro and confirm it converts without executing the macro
- [ ] **faster-whisper int8 mode:** CPU-compatible precision — verify `compute_type="int8"` in the model initialization; if `"float16"` appears anywhere in the transcription code on the x86_64 server, it will fail at runtime
- [ ] **Home server publicly accessible:** Transcription endpoint reachable from outside the local network — verify by hitting the transcription endpoint from a non-local network (e.g., mobile data) before wiring up the MCP tool
- [ ] **Temp file cleanup:** Files not accumulating — verify by running 20 conversion requests and checking `/tmp` for leftover files; they should all be gone after each request completes
- [ ] **Playwright timeout set:** Default timeout overridden — verify `page.set_default_timeout(8000)` or equivalent appears in the scraping request handler
- [ ] **Rate limits active:** Per-wallet limits enforced — verify by sending 11 email requests from the same wallet address and confirming request 11 returns a 429
- [ ] **Free test endpoints:** All 5 new APIs have free test mode — verify each endpoint works with no `X-PAYMENT` header on the designated test input (same pattern as screenshot/PDF/sentiment free tier)
- [ ] **MCP tool descriptions:** Prices and limitations accurate — verify tool descriptions mention the enforced size/rate limits so agents know the constraints upfront

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| MLX Whisper fails on Intel home server | LOW | Uninstall mlx packages; `pip install faster-whisper`; update transcription service code to use `faster_whisper.WhisperModel` API; redeploy |
| Playwright OOM kills Railway container | MEDIUM | Switch to persistent browser pool (requires refactor); upgrade Railway plan to 1GB memory; deploy and verify with load test |
| Resend domain reputation damaged by spam | HIGH | Contact Resend support immediately; add rate limiting retroactively; the domain's reputation may take weeks to recover — consider registering a new dedicated sender subdomain (e.g., `api-mail.x402.network`) |
| Search API monthly budget exhausted | LOW | Enable hard spend cap in provider dashboard; add per-wallet rate limiting; wait for billing cycle reset (no permanent damage) |
| LibreOffice container cold start too slow | MEDIUM | Add pre-warm subprocess call in FastAPI lifespan event; if still too slow, consider separating LibreOffice into its own Railway service and queue-based communication |
| Temp files fill Railway container filesystem | LOW | Railway restart clears ephemeral filesystem; add cleanup code; redeploy |
| Home server transcription unreachable externally | LOW | Configure router port forwarding; update `src/index.ts` with public URL; republish npm package if URL is hardcoded |
| SSRF attack exfiltrates Railway env vars | HIGH | Rotate all environment variables (API keys, Resend key, search API key) immediately; add SSRF protection; audit Railway service logs for suspicious requests |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| MLX Whisper incompatible with Intel x86_64 | Phase 1: transcription backend | `uname -m` on home server; `import faster_whisper` succeeds |
| Playwright missing system deps in container | Phase 1: web scraping backend | Docker build + local container test with Playwright launch |
| Playwright OOM at 512MB | Phase 1: web scraping backend | Persistent browser pool in code; Railway plan set to 1GB |
| Playwright anti-bot detection | Phase 1: web scraping backend | `playwright-stealth` in deps; challenge page detection in response |
| Resend from-address requires domain verification | Phase 1: email backend (before any code) | Resend dashboard shows domain "Verified"; test email shows `dkim=pass` |
| Resend abuse surface (open relay) | Phase 1: email backend | Rate limiting code in place; HTML body rejected; logging enabled |
| Search API cost spike | Phase 1: search backend | Provider billing alert set; per-wallet rate limit in code |
| LibreOffice image size and cold start | Phase 1: file conversion backend | Docker image < 800MB; pre-warm in lifespan event |
| Temp file accumulation | Phase 1: file conversion backend | `TemporaryDirectory` context manager in all conversion handlers |
| SSRF on URL-fetch endpoints | Phase 1: all backends that accept URLs | SSRF validation function present; 422 on private IP test |
| Playwright timeout cascade | Phase 1: web scraping backend | `set_default_timeout(8000)` in request handler |
| Large audio file hangs transcription | Phase 1: transcription backend | 25MB size limit + 10min duration limit + subprocess timeout |
| Home server not publicly accessible | Phase 1: transcription backend | Hit transcription endpoint from mobile data connection; confirm 200 |
| MCP tool descriptions without limits | Phase 2: MCP server update | Tool descriptions mention enforced limits; prices match backend |
| No free test endpoints | Phase 2: MCP server update | Each new tool has free test mode verified end-to-end |

---

## Sources

- Playwright Docker: https://playwright.dev/python/docs/docker — official base images; system dependency requirements
- Playwright anti-bot: https://github.com/AtuboDad/playwright_stealth — stealth mode for Python
- MLX platform requirements: https://github.com/ml-explore/mlx — "MLX is available on devices with Apple silicon" — no Intel support
- faster-whisper: https://github.com/SYSTRAN/faster-whisper — CTranslate2-based Whisper for CPU; `compute_type="int8"` for CPU inference
- Resend domain setup: https://resend.com/docs/dashboard/domains/introduction — SPF/DKIM/DMARC requirements
- Resend rate limits: https://resend.com/docs/api-reference/introduction — 100 reqs/sec; per-account limits
- LibreOffice in Docker: https://hub.docker.com/r/linuxserver/libreoffice — image size reference; `--noscripting` flag
- SSRF prevention: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html — RFC 1918 block list
- Railway memory limits: https://docs.railway.app/reference/pricing — 512MB starter, 1GB recommended for browser workloads
- SerpAPI / Brave / Tavily pricing: provider dashboards — flat per-query pricing; hard monthly caps available
- Personal experience: existing Railway deployments (screenshot, PDF, sentiment APIs); home server at 10.0.0.2 (macOS Monterey, Intel x86_64, confirmed via PROJECT.md)

---
*Pitfalls research for: Universal Utility APIs v1.1 — Web Scraping, Email, Search, File Conversion, Audio Transcription*
*Researched: 2026-03-12*
