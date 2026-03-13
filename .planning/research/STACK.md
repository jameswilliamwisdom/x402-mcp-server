# Stack Research

**Domain:** v1.1 Universal Utility APIs — 5 new backend services + MCP tool additions
**Researched:** 2026-03-12
**Confidence:** HIGH

## Context

The existing stack is locked in and working:
- **MCP server:** TypeScript, `@modelcontextprotocol/sdk ^1.11.0`, `viem ^2.0.0`, `x402-fetch ^1.1.0`, `zod ^4.3.6`
- **API pattern:** Python/FastAPI on Railway with `fastapi-x402` (proven with screenshot, PDF, crypto sentiment)
- **Home server:** macOS Monterey x86_64 at 10.0.0.2 (nginx, for transcription only)

This research covers ONLY what's new for the 5 new APIs. Do not re-research the existing stack.

---

## API 1: Web Scraping (Railway)

**Approach:** Python/FastAPI — same pattern as screenshot and PDF APIs.

### Python Backend Libraries

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `playwright` | `^1.58.0` | Headless browser, full JS rendering | Matches the existing screenshot API approach; handles SPAs and JS-heavy sites; asyncio-native |
| `beautifulsoup4` | `^4.12.3` | HTML parsing + structured extraction | Industry standard; lxml backend; use alongside playwright for post-render parsing |
| `lxml` | `^5.3.0` | Fast XML/HTML parser backend for BS4 | Faster than html.parser, required as BS4 backend for production use |

**Note on Cheerio:** The original plan mentions Cheerio, but this runs on the Python/FastAPI backend on Railway, not in the MCP server TypeScript layer. Use BeautifulSoup4 with lxml instead. Cheerio would only apply if the scraper were reimplemented in Node.js.

### Installation

```bash
pip install playwright beautifulsoup4 lxml
playwright install chromium
```

### Pattern Match

Follows existing screenshot API pattern — stateless POST with `url` param, returns structured JSON. Add `/test/scrape` free endpoint limited to safe domains.

---

## API 2: Email Sending (Railway)

**Decision:** Resend. Already chosen in PROJECT.md. No research needed for the choice, only for the implementation library.

### Python Backend Libraries

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `resend` | `^2.x` (latest ~Feb 2026) | Official Resend Python SDK | Type-hinted SDK 2.0; `pip install resend`; simple `resend.Emails.send({...})` API |

### Installation

```bash
pip install resend
```

### Environment Variables

```bash
RESEND_API_KEY=re_xxx
```

### Integration

```python
import resend

resend.api_key = os.environ["RESEND_API_KEY"]
r = resend.Emails.send({
    "from": "api@x402.network",
    "to": params["to"],
    "subject": params["subject"],
    "html": params["body"],
})
```

Stateless — no domain config state needed if using a verified Resend domain. Price cap: $0.01 per send.

---

## API 3: Web Search (Railway) — Decision Required

This is the only API where the backend provider is undecided. Three candidates: SerpAPI, Brave Search API, Tavily.

### Search Backend Comparison

| Factor | SerpAPI | Brave Search | Tavily |
|--------|---------|--------------|--------|
| **What it is** | SERP scraper proxy — wraps Google, Bing, 40+ engines | Independent search index, privacy-first, no tracking | AI-native search API — aggregates sources, returns LLM-ready snippets + citations |
| **Free tier** | 250 searches/month | $5 monthly credits (~1,000 queries); free tier dropped Feb 12, 2026 | 1,000 credits/month, no credit card required |
| **Pay-as-you-go** | No PAYG — subscription only | $3–$5 CPM ($3–$5 per 1,000 queries) | $0.008/credit ($8 per 1,000 basic searches) |
| **Subscription cost** | $75/month for 5,000 searches ($15/1k); credits expire monthly | None required — metered billing from $3 CPM | $0.005–$0.0075/credit at scale; no rollover |
| **Rate limits** | Hourly cap: 20% of plan volume (1,000/hr on $75 plan) | Plan-dependent, not publicly documented | Not publicly documented per tier |
| **Result quality** | Raw SERP data — Google/Bing rankings, no summarization | Independent index — unbiased from Google/Bing; good freshness | Aggregated + AI-ranked; returns clean snippets, no raw SERP noise |
| **LLM/agent fit** | Poor — returns raw HTML-ish SERP data; requires your own parsing | Moderate — clean JSON results, but still raw search hits | Best — purpose-built for LLM consumption; returns structured excerpts |
| **Python SDK** | `google-search-results` (pip) | No official SDK; simple REST GET | `tavily-python` (pip), `>=3.8` |
| **Dependency risk** | High — depends on Google not blocking; ToS risk | Low — own index, stable | Low — own infrastructure |
| **Gotcha** | Unused credits don't roll over on any plan; forces over-provisioning | Attribution required for free credits | Credits don't roll over monthly |

### Recommendation: Tavily

**Use Tavily** for the web search API backend.

**Why:**
1. **LLM-ready output by design.** Tavily returns structured JSON with `title`, `url`, `content` (relevant excerpt), and `score` — exactly what an MCP tool should hand back to an agent. No parsing layer needed.
2. **Free tier works for development.** 1,000 credits/month, no credit card — lowers barrier to get started and test the API without spend.
3. **Micropayment alignment.** At $0.008/search PAYG, the x402 markup can be $0.01/search, maintaining the "sub-$0.10" constraint comfortably.
4. **No subscription trap.** SerpAPI's subscription-only pricing with expiring credits is incompatible with the pay-per-use model — you'd be paying fixed cost regardless of actual x402 API usage.
5. **Dependency stability.** Uses its own infrastructure, not a wrapper around Google that can break.

**When Brave is better:** If you specifically need a privacy-first, Google-independent index and your users care about unbiased results (e.g., competitive intelligence). The independent index is Brave's genuine differentiator. At $3 CPM it's slightly cheaper than Tavily PAYG at the unit level, but requires attribution and the SDK situation is worse.

**When SerpAPI is better:** If you need Google SERP data specifically (ads, shopping results, local packs) and are willing to pay a subscription. Never for this use case.

### Python Backend Libraries

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `tavily-python` | `^0.5.x` (latest Feb 2026) | Official Tavily Python SDK | Simple `TavilyClient(api_key=...).search(query)` interface; returns structured JSON |

### Installation

```bash
pip install tavily-python
```

### Environment Variables

```bash
TAVILY_API_KEY=tvly-xxx
```

### Integration

```python
from tavily import TavilyClient

client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
results = client.search(
    query=params["query"],
    max_results=params.get("max_results", 5),
    search_depth="basic",  # or "advanced" (2 credits)
)
# Returns: {"results": [{"title": ..., "url": ..., "content": ..., "score": ...}]}
```

---

## API 4: File Conversion (Railway)

Four conversion types: doc-to-pdf, image resize, html-to-pdf, csv-to-json. Each has different library needs.

### Python Backend Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `WeasyPrint` | `^68.1` (released Feb 6, 2026) | HTML → PDF | Primary html-to-pdf conversion; pure Python CSS layout engine; no headless browser needed; requires Python >=3.10 |
| `Pillow` | `^12.1.1` (released Feb 11, 2026) | Image resize, format conversion | All image operations; format conversion (PNG→JPEG, etc.); thumbnail generation; the standard |
| `python-docx` | `^1.1.2` | Read `.docx` content | For DOCX inspection — but NOT for DOCX-to-PDF conversion (use LibreOffice for that) |
| `pypdf` | `^4.x` | PDF read/merge | Only if PDF manipulation (merge, split) is needed beyond conversion |

### DOCX-to-PDF: LibreOffice via subprocess

**Do NOT use `python-docx` alone for doc-to-pdf.** It reads DOCX but cannot render to PDF with accurate formatting.

**Use LibreOffice headless via subprocess:**

```python
import subprocess
subprocess.run([
    "libreoffice", "--headless", "--convert-to", "pdf",
    "--outdir", output_dir, input_path
], check=True)
```

Railway's Docker image can include LibreOffice:
```dockerfile
RUN apt-get install -y libreoffice --no-install-recommends
```

This is the production-proven approach. Conversion time on Railway: ~1-2 seconds per document.

**Alternative considered: `docx2pdf`** — This is a thin wrapper that calls LibreOffice or Microsoft Word depending on platform. On Linux Railway it calls LibreOffice anyway, so use LibreOffice subprocess directly for control.

**Alternative considered: `unoconv`** — Deprecated; uses the same LibreOffice backend but adds an unstable Python 2 layer. Do not use.

### CSV-to-JSON: stdlib only

```python
import csv, json

def csv_to_json(content: str) -> list[dict]:
    reader = csv.DictReader(content.splitlines())
    return list(reader)
```

No library needed. Python's `csv.DictReader` handles the conversion. Keep it simple.

### Installation

```bash
pip install weasyprint pillow python-docx
```

Dockerfile addition for LibreOffice:
```dockerfile
RUN apt-get update && apt-get install -y libreoffice --no-install-recommends && rm -rf /var/lib/apt/lists/*
```

### Sizing Note

LibreOffice adds ~300MB to the Railway Docker image. This is the main cost tradeoff — acceptable for a file conversion service.

---

## API 5: Audio Transcription (Home Server — NOT Railway)

**Critical finding: MLX Whisper does NOT run on Intel Mac (x86_64).**

MLX is Apple's array framework designed exclusively for Apple Silicon (M1/M2/M3/M4). The PyPI package only ships `macosx_*_arm64` wheels. It will not install or run on macOS Monterey x86_64.

### The Intel Mac Problem

The home server at 10.0.0.2 is macOS Monterey x86_64. MLX Whisper is not an option. This changes the transcription deployment entirely.

### Recommended Alternative: faster-whisper

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `faster-whisper` | `^1.2.1` (latest 2026) | Audio transcription on CPU | CTranslate2-based reimplementation; 4x faster than `openai-whisper` at same accuracy; explicit x86_64 CPU support via Intel MKL backend; 8-bit quantization reduces memory |

`faster-whisper` uses CTranslate2 which supports x86_64 via Intel MKL and OpenBLAS. This is the right choice for an Intel Mac server.

### Alternative: openai-whisper

`openai-whisper` (version 20250625, released June 2025) also runs on Intel Mac via PyTorch CPU mode. However, it is 4x slower than `faster-whisper` for the same model and accuracy. Use `faster-whisper` unless PyTorch compatibility is specifically needed.

### Installation on Intel Mac

```bash
pip install faster-whisper
```

No special flags needed. CTranslate2 wheels for macOS x86_64 are available on PyPI.

### Model Choice for Intel Mac

```python
from faster_whisper import WhisperModel

# For Intel Mac: use "medium" or "medium.en" for English
# int8 quantization reduces memory without significant accuracy loss on CPU
model = WhisperModel("medium.en", device="cpu", compute_type="int8")

segments, info = model.transcribe("audio.mp3", beam_size=5)
transcript = " ".join([s.text for s in segments])
```

On Intel Mac CPU, `medium.en` with int8 is the practical sweet spot:
- `tiny.en` / `base.en` — too fast to matter but noticeably less accurate
- `large-v3` — too slow on CPU for a responsive API (minutes per minute of audio)
- `medium.en` + int8 — ~real-time factor of 2-4x on modern Intel i7/i9

### Deployment Pattern

Unlike the Railway services, the transcription API runs directly on the home Mac server via FastAPI + uvicorn, proxied through the existing nginx on port 8888. Same `fastapi-x402` middleware pattern applies — it's still a FastAPI service.

```bash
uvicorn transcription_api:app --host 0.0.0.0 --port 8001
```

Nginx proxies `/transcribe` to `:8001`. The MCP server calls `http://10.0.0.2:8888/transcribe` (same nginx gateway as the brand site).

### Audio Format Handling

```bash
pip install faster-whisper ffmpeg-python
```

`faster-whisper` uses `ffmpeg` internally — ensure ffmpeg is installed on the Mac server:
```bash
brew install ffmpeg
```

Accept audio URLs (download to temp file, transcribe, delete). Support: mp3, mp4, m4a, wav, ogg, webm.

---

## MCP Server Updates (TypeScript)

The MCP server in `src/index.ts` requires no new runtime dependencies. All 5 new APIs follow the existing `apiGet`/`apiPost` helper pattern with `x402-fetch`.

**Changes needed:**
1. Add 5 new API entries to the `APIS` const object
2. Add ~2 tools per new API (test + paid mode)
3. Update `package.json` version to `1.1.0`
4. Update `description` and `keywords` fields

No new npm packages required in the MCP server itself.

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `mlx-whisper` | Apple Silicon only; will not install on macOS x86_64 | `faster-whisper` — explicit x86_64 CPU support via CTranslate2 |
| `openai-whisper` (for production) | 4x slower than faster-whisper at same accuracy on CPU | `faster-whisper ^1.2.1` |
| `PyPDF2` | Deprecated; no longer maintained | `pypdf` (successor project by same maintainers) |
| `unoconv` | Deprecated Python 2 wrapper around LibreOffice; unreliable on modern systems | LibreOffice `--headless` subprocess directly |
| `docx2pdf` | Just wraps LibreOffice anyway on Linux; adds unnecessary abstraction | LibreOffice subprocess directly |
| SerpAPI | Subscription-only with expiring credits; incompatible with pay-per-use model; 4x more expensive at volume | Tavily |
| `@x402/fetch` (scoped) | Non-functional stub package — confirmed gotcha from v1.0 | `x402-fetch` (non-scoped, already in use) |
| `cheerio` (npm) | Not applicable — backend is Python/FastAPI, not Node.js | `beautifulsoup4` + `lxml` |
| Playwright MCP / Puppeteer MCP | For the Python Railway backend, use `playwright` Python package | `playwright` (Python, PyPI) |

---

## Stack Patterns by API Host

**Railway services (Web Scraping, Email, Search, File Conversion):**
- Same FastAPI + `fastapi-x402` pattern as screenshot/PDF APIs
- Python 3.11+ (Railway default)
- `requirements.txt` per service
- Dockerfile only if extra system deps needed (LibreOffice for file conversion)
- Free test endpoint at `/test/<endpoint>` with safe input restrictions

**Home server (Transcription):**
- FastAPI + `fastapi-x402` — same middleware pattern, different host
- Python 3.11+ (install via pyenv on Mac)
- Service: uvicorn on :8001, nginx proxy on :8888
- `faster-whisper` model loaded at startup (not per-request)
- Model warm-up on first request (5-15 seconds cold start) — acceptable for a home server

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `WeasyPrint ^68.1` | Python >=3.10 | Dropped Python 3.9 — use Railway Python 3.11+ |
| `faster-whisper ^1.2.1` | Python >=3.8, macOS x86_64 | CTranslate2 has x86_64 wheels; no ARM-only restriction |
| `playwright ^1.58.0` (Python) | Python >=3.9 | Requires `playwright install chromium` post-install; add to Railway Dockerfile or Procfile |
| `Pillow ^12.1.1` | Python >=3.9 | No breaking changes from 10.x for resize/format operations |
| `tavily-python` | Python >=3.8 | Simple REST wrapper; no version conflicts expected |
| `resend ^2.x` | Python >=3.7 | SDK 2.0 has type hints; use `resend.Emails.send({...})` pattern |

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `faster-whisper` | `openai-whisper` | When you need PyTorch ecosystem compatibility or are testing on Apple Silicon where MLX is available |
| `WeasyPrint` | Playwright HTML→PDF | When pixel-perfect CSS/JS rendering is needed (WeasyPrint doesn't run JS); Playwright is heavier but handles JS-rendered pages |
| Tavily | Brave Search API | When you need a Google/Bing-independent index and your users value privacy-first results; attribution required |
| Tavily | SerpAPI | When you specifically need raw Google SERP data (ads, shopping boxes, local results) — never for agent/LLM use case |
| LibreOffice subprocess | `python-docx` + `reportlab` | When you can't add 300MB to the Docker image; limited to simple documents only |
| BeautifulSoup4 + lxml | `html5lib` parser | When strict HTML5 spec conformance is more important than speed; slower but more tolerant of malformed HTML |

---

## Full Installation Summary

### Per Railway Service

**Web Scraping API (`requirements.txt`):**
```
fastapi
fastapi-x402
uvicorn[standard]
playwright==1.58.0
beautifulsoup4>=4.12.3
lxml>=5.3.0
```
Post-install: `playwright install chromium --with-deps`

**Email Sending API (`requirements.txt`):**
```
fastapi
fastapi-x402
uvicorn[standard]
resend>=2.0.0
```

**Web Search API (`requirements.txt`):**
```
fastapi
fastapi-x402
uvicorn[standard]
tavily-python>=0.5.0
```

**File Conversion API (`requirements.txt` + Dockerfile):**
```
fastapi
fastapi-x402
uvicorn[standard]
weasyprint>=68.1
Pillow>=12.1.1
python-docx>=1.1.2
```
```dockerfile
RUN apt-get update && apt-get install -y libreoffice --no-install-recommends && rm -rf /var/lib/apt/lists/*
```

### Home Server (Transcription)

```bash
pip install faster-whisper fastapi fastapi-x402 uvicorn ffmpeg-python
brew install ffmpeg  # system dependency
```

### MCP Server (TypeScript) — No New Dependencies

```bash
# No changes to package.json dependencies
# Only src/index.ts additions and version bump to 1.1.0
```

---

## Sources

- [pypi.org/project/faster-whisper](https://pypi.org/project/faster-whisper/) — v1.2.1 confirmed, CTranslate2 x86_64 support verified
- [github.com/ml-explore/mlx](https://github.com/ml-explore/mlx) — Apple Silicon only, arm64 wheels only, confirmed no x86_64 support
- [pypi.org/project/weasyprint](https://pypi.org/project/weasyprint/) — v68.1 released Feb 6, 2026; Python >=3.10 required
- [pypi.org/project/pillow](https://pypi.org/project/pillow/) — v12.1.1 released Feb 11, 2026
- [pypi.org/project/tavily-python](https://pypi.org/project/tavily-python/) — confirmed latest Feb 2026; `pip install tavily-python`
- [pypi.org/project/resend](https://pypi.org/project/resend/) — SDK 2.0, Feb 2026; type hints, Python >=3.7
- [pypi.org/project/playwright](https://pypi.org/project/playwright/) — v1.58.0, released Jan 30, 2026; Python >=3.9
- [docs.tavily.com/documentation/api-credits](https://docs.tavily.com/documentation/api-credits) — 1,000 free credits/month; $0.008/credit PAYG
- [brave.com/search/api](https://brave.com/search/api/) — $3-$5 CPM; free tier dropped Feb 12, 2026; $5 monthly credits now
- [serpapi.com/pricing](https://serpapi.com/pricing) — $75/month for 5,000 searches; credits expire; no PAYG
- [implicator.ai/brave-drops-free-search-api-tier](https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing/) — Brave free tier removal confirmed
- [dev.to/ritza/best-serp-api-comparison-2025](https://dev.to/ritza/best-serp-api-comparison-2025-serpapi-vs-exa-vs-tavily-vs-scrapingdog-vs-scrapingbee-2jci) — comparative analysis

---
*Stack research for: x402 API Network — v1.1 Universal Utility APIs (5 new backends)*
*Researched: 2026-03-12*
