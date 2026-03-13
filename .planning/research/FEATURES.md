# Feature Research

**Domain:** 5 new universal utility APIs — v1.1 milestone (web scraping, email sending, web search, file conversion, audio transcription)
**Researched:** 2026-03-12
**Confidence:** HIGH

---

## API 1: Web Scraping + Structured Extraction

### How It Works

Send a URL. The API fetches the page with a headless browser (Playwright), extracts content, and returns structured JSON. The key value-add over a raw HTTP fetch is JS-rendered content, clean text extraction, and structured output — not raw HTML.

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| URL → clean markdown text | Core output format; what every LLM wants to consume | LOW | Strip nav, footer, ads — main content only. Cheerio post-process after Playwright render. |
| Extracted links array | Standard scrape output; agents use links for further crawling | LOW | Absolute URLs only — resolve relative links against base URL before returning |
| Page metadata (title, description, OG tags) | Basic context without reading full body | LOW | Parse `<title>`, `<meta name="description">`, `<meta property="og:*">` |
| HTTP error surfacing | Users need to know if the target returned 4xx/5xx | LOW | Return status code + error type in response, not just a generic failure |
| Timeout parameter | Slow pages are common; callers need control | LOW | Default 15s, max 60s. Railway has a 60s request timeout anyway. |
| JS rendering support | SPAs are the majority of modern pages; static fetch is useless for them | MEDIUM | This is why Playwright is in the stack. Ensure it's actually used, not just available. |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `wait_for` selector parameter | Wait until a specific DOM element appears before extracting — handles async data loads | MEDIUM | Playwright `.waitForSelector()`. Firecrawl offers this but it's often missing from budget scrapers. |
| `only_main_content` boolean (default true) | Strip nav/header/footer/ads automatically — LLM-ready by default | LOW | Readability-style extraction. Firecrawl's `onlyMainContent` is their most-used parameter. |
| Tables extracted as JSON arrays | Tables in markdown are ugly; returning them as structured arrays makes agents much more useful | MEDIUM | Cheerio table parsing → array of objects keyed by header row. Edge case: merged cells. |
| `extract` schema parameter | Caller provides a JSON schema; API returns structured data matching the schema | HIGH | Firecrawl's killer feature. Uses LLM to fill schema from page content. Expensive — skip for v1.1, document as v1.2 target. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full crawl (follow links, multi-page) | "Scrape a whole site" is a common ask | Railway request timeout is 60s; multi-page crawl is minutes of work; billing model doesn't fit micropayment | Single-page only. Agent can call the tool in a loop for multi-page workflows. |
| Screenshot return alongside text | "Give me both" seems natural | Doubles response payload; screenshot tool already exists | Separate tools — use `x402_screenshot` + `x402_scrape`. Compose at the agent level. |
| Cookie/session injection | Login-walled content | Security scope creep; session management state doesn't fit stateless model | Not supported. Document explicitly. |
| Proxy rotation | Bypassing bot detection | Increases infra cost significantly; legal gray area for some sites | Single egress IP is fine for most content. Sites that block it are out of scope. |

### Parameter Schema

```
url              string, required — Full URL to scrape (https:// only)
wait_for         string, optional — CSS selector to wait for before extracting (default: none)
timeout          integer, optional — Max wait time in seconds (default: 15, max: 60)
only_main_content boolean, optional — Strip nav/header/footer/ads (default: true)
include_tables   boolean, optional — Extract HTML tables as JSON arrays (default: true)
include_links    boolean, optional — Include extracted links array (default: true)
```

### Response Format

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "description": "This domain is for use in examples.",
  "markdown": "# Example Domain\n\nThis domain is for use...",
  "links": [
    { "text": "More information", "href": "https://www.iana.org/domains/example" }
  ],
  "tables": [
    [
      { "header1": "value1", "header2": "value2" },
      { "header1": "value3", "header2": "value4" }
    ]
  ],
  "metadata": {
    "og_title": "Example Domain",
    "og_description": null,
    "og_image": null
  },
  "status_code": 200,
  "scraped_at": "2026-03-12T00:00:00Z"
}
```

### Edge Cases

- **JS-heavy SPAs** that need multiple network roundtrips to render — `wait_for` selector is the escape hatch
- **Paywalled content** — returns whatever the public unauthenticated view shows; document this clearly
- **Infinite scroll pages** — only captures what's in the initial viewport/render cycle
- **PDF links** — should return error suggesting `x402_pdf_extract` instead
- **Non-UTF-8 encoding** — Playwright handles this; Cheerio may need explicit encoding detection
- **Very large pages** (>5MB HTML) — truncate markdown output at ~50KB with a `truncated: true` flag

### Complexity: MEDIUM

Playwright + Cheerio are already in the project plan. The tricky parts are: ensuring Playwright is actually doing JS rendering (not just HTTP fetch), robust `only_main_content` extraction, and table parsing. Free test endpoint: use `example.com`, `httpbin.org/html`, and one JS-heavy public page.

---

## API 2: Email Sending

### How It Works

Stateless send: caller provides `to`, `from`, `subject`, `html`/`text`. API calls Resend's API and returns success/failure with the Resend message ID. No state stored, no tracking, no open/click data. One tool call = one email.

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| HTML email body | Every real email uses HTML | LOW | Pass directly to Resend `html` field |
| Plain text fallback | Email clients that don't render HTML; spam filters penalize HTML-only | LOW | Resend auto-generates plain text from HTML if `text` is not provided — document this |
| Multiple `to` recipients (array) | Common pattern | LOW | Resend supports array of up to 50 addresses |
| `reply_to` address | Near-universal expectation | LOW | Resend `reply_to` field |
| Delivery confirmation (message ID) | Callers need to know if the send succeeded | LOW | Return Resend's `id` field (`re_abc123...`) |
| Clear error messaging | DNS errors, invalid addresses, Resend rejections | LOW | Surface Resend's error codes and messages verbatim |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `from` address validation against verified domains | Prevents silent failures when callers use unverified sender domains | LOW | Resend will reject unverified senders — surface the error clearly with a helpful message explaining domain verification |
| `cc` and `bcc` support | Completeness; common in transactional flows | LOW | Resend supports both — just pass through |
| Subject line templating note in docs | Agents often want `Hello {{name}}` style templates | LOW | Not an API feature — document that callers should pre-interpolate strings before calling. Prevents agents from expecting server-side templating that doesn't exist. |
| Idempotency key support | Prevents duplicate sends on retry | LOW | Pass `X-Idempotency-Key` header through to Resend. Useful when agents retry on transient errors. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Email scheduling | "Send at 9am tomorrow" is a common ask | Requires server-side state; breaks stateless model | Caller handles scheduling at their layer; this tool sends on demand |
| Open/click tracking | "Did they read it?" | Requires pixel injection and redirect infrastructure; Resend's tracking requires their CDN; adds privacy concerns | Out of scope. Resend's dashboard shows delivery events for the account holder. |
| Attachment upload | "Include a file" | Multipart form data + file storage is a different integration surface | Out of scope for v1.1. Resend supports attachments via base64 in the API body — viable as v1.2. |
| Bulk/batch send (array of emails) | "Send 1000 emails" | Pricing model doesn't fit; micropayment per-call model conflicts with bulk discount expectations | Caller loops; each email is one API call and one micropayment |
| Unsubscribe / list management | CAN-SPAM compliance | Requires persistent list state; this is an MTA not an ESP | Use Resend or a real ESP for list-based email |

### Parameter Schema

```
to               string or array<string>, required — Recipient(s), max 50
from             string, required — Sender address (must be verified in Resend, e.g., "Name <email@domain.com>")
subject          string, required — Email subject line
html             string, optional — HTML body (at least one of html or text required)
text             string, optional — Plain text body (auto-generated from html if omitted)
cc               string or array<string>, optional — CC recipients
bcc              string or array<string>, optional — BCC recipients
reply_to         string or array<string>, optional — Reply-to address(es)
idempotency_key  string, optional — Unique key to prevent duplicate sends on retry
```

### Response Format

```json
{
  "id": "re_abc123xyz",
  "status": "sent",
  "to": ["recipient@example.com"],
  "from": "Sender Name <sender@verified.com>",
  "subject": "Hello from x402"
}
```

Error response:

```json
{
  "error": "validation_error",
  "message": "The 'from' address domain is not verified in Resend. Visit https://resend.com/domains to add and verify your domain.",
  "status_code": 422
}
```

### Edge Cases

- **Unverified `from` domain** — Resend will hard-reject; surface with actionable error message pointing to domain verification
- **Invalid email addresses** — Resend validates format; surface their error
- **Free test endpoint** — must not actually send real emails; either use Resend's sandbox mode or a hardcoded test recipient. Resend does not have a native sandbox — use a `+test` address or the `onboarding@resend.dev` demo sender for the free tier.
- **HTML injection** — callers control their own HTML body; this is intentional, not a vulnerability
- **`from` display name with quotes** — `"My Company" <sender@domain.com>` — ensure quotes are handled correctly when passed to Resend

### Complexity: LOW

Resend's Node SDK is trivial. The Python `resend` package exists for FastAPI. The only non-trivial piece is making the free test endpoint safe (not sending real emails) and surfacing Resend error messages helpfully. Backend on Railway, Resend API key as env var.

---

## API 3: Web Search

### How It Works

Send a text query, get back a ranked list of results with title, URL, and snippet. The value is clean structured JSON output, not a raw SERP scrape. No ads, no knowledge panels — just the organic results agents actually need.

### Search Backend Decision

**Recommended: Tavily**
- Purpose-built for AI agents and LLM workflows
- Returns LLM-ready content (summaries, relevance scores, pre-trimmed snippets)
- Structured JSON designed for direct injection into agent context
- Free tier: 1,000 requests/month — sufficient for free test endpoint
- Pricing: 1 credit per basic search, 2 for advanced (with content extraction)
- No scraping required — they handle legality and ToS

**Alternatives considered:**
- **Brave Search API**: Clean JSON, no personal data, $3/1000 queries. Good choice if Tavily pricing is a concern. Returns standard SERP fields.
- **SerpAPI**: Google results, but expensive ($50+/month for real volume) and ToS risks.
- **DuckDuckGo (unofficial)**: Free but unofficial, fragile, ToS violation.

**Decision rationale:** Tavily's agent-optimized output means less post-processing in the API layer. The response is already what an agent needs. Use Tavily basic search at $0.01/query pricing equivalent.

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| query → array of {title, url, snippet} | The core contract of a search API | LOW | Map Tavily results to this normalized schema |
| `num_results` parameter | Different use cases need different result counts | LOW | Default 5, max 10. Tavily returns up to 10. |
| Each result has a usable URL | Agents follow up by scraping results — URL must be the real destination | LOW | Tavily returns direct URLs, not redirect chains |
| Relevance ordering | Results should be most-to-least relevant | LOW | Tavily handles this; just preserve the order |
| Error on empty/nonsense query | Input validation before calling paid backend | LOW | Zod validation: min 2 chars, max 400 chars |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `include_answer` boolean | Tavily can synthesize a direct answer from search results — agent gets answer + sources in one call | LOW | Map to Tavily's `include_answer` parameter. Returns a summary string above the results array. |
| `search_depth` parameter (basic/advanced) | Advanced mode does content extraction for deeper results — worth the 2x credit cost for research tasks | LOW | Expose as parameter. Price `advanced` at $0.02 vs $0.01 for `basic`. |
| `include_domains` / `exclude_domains` arrays | Focus search on trusted sources or exclude noise sites | LOW | Pass through to Tavily. Useful for agents doing domain-specific research. |
| Result `score` field | Callers can threshold by relevance (e.g., ignore results below 0.5) | LOW | Tavily returns relevance scores — include in response |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Image search | "Find images of X" | Different endpoint, different result schema, different use cases | Separate tool if there's demand — not v1.1 |
| News-only search | "Latest news about X" | Tavily has topic filtering — but adding `topic` param increases API surface area | Use `include_domains` to constrain to news sites as a workaround |
| Caching results | "Don't charge me for the same query" | Breaks the stateless model; adds Redis/database dependency | Not the right layer for caching — caller can cache if needed |
| Raw SERP HTML | "I want to parse it myself" | Defeats the purpose; huge payload | Use `x402_scrape` on a search URL if truly needed |

### Parameter Schema

```
query            string, required — Search query (min 2 chars, max 400 chars)
num_results      integer, optional — Number of results to return (default: 5, max: 10)
search_depth     enum("basic", "advanced"), optional — basic = snippets only, advanced = content extraction (default: "basic")
include_answer   boolean, optional — Include a synthesized direct answer above results (default: false)
include_domains  array<string>, optional — Restrict results to these domains (e.g., ["github.com", "stackoverflow.com"])
exclude_domains  array<string>, optional — Exclude results from these domains
```

### Response Format

```json
{
  "query": "x402 payment protocol",
  "answer": "The x402 protocol is a proposed web payment standard based on the HTTP 402 status code...",
  "results": [
    {
      "title": "x402: HTTP Native Payments",
      "url": "https://x402.org",
      "snippet": "x402 is an open protocol for HTTP-native micropayments using the existing 402 Payment Required status code...",
      "score": 0.95,
      "published_date": "2025-11-01"
    }
  ],
  "num_results": 5,
  "search_depth": "basic"
}
```

### Edge Cases

- **Query with special characters** — URL-encode before sending to Tavily
- **No results found** — return empty `results` array with `num_results: 0`, not an error
- **Tavily rate limit hit** — surface as a retryable error with `retry_after` hint
- **`include_answer` with no good answer available** — Tavily may return null; handle gracefully (omit field or return null)
- **`advanced` depth with blocked domains** — Tavily's content extraction may fail on some sites; individual result `content` may be null

### Complexity: LOW

Tavily has a clean Python SDK (`tavily-python`). The API layer is thin — validate input, call Tavily, normalize response. The only decision is whether to expose Tavily's full parameter surface or keep it focused. Keep it focused: the 6 parameters above are sufficient for 95% of agent use cases.

---

## API 4: File Conversion

### How It Works

Send a file URL and a target format. API downloads the file, converts it, and returns the result as a base64-encoded blob or a URL to a temporary output file. No state — input URL in, converted file out.

### Supported Conversion Types (v1.1)

| Input → Output | Use Case | Library |
|----------------|----------|---------|
| HTML → PDF | Render web pages as PDF documents | Playwright (already in stack) |
| doc/docx → PDF | Convert Word docs to PDF | LibreOffice headless (`soffice --headless`) |
| image → resized image | Resize/reformat images | Pillow (Python) |
| CSV → JSON | Tabular data normalization | Python `csv` stdlib |

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `input_url` + `output_format` as the core interface | The minimum viable API surface for any file converter | LOW | Download input, convert, return output |
| Base64-encoded output in response | No need for a separate download step — agent gets the file directly | LOW | For small files (<5MB). Same pattern as screenshot API. |
| MIME type in response | Callers need to know what they received | LOW | Return `content_type: "application/pdf"` etc. |
| Input file size limit with clear error | Large files = timeout = bad UX | LOW | Reject files >10MB with a clear size limit error before attempting download |
| Supported formats list in error message | When an unsupported conversion is requested | LOW | Return `"supported_conversions": ["html→pdf", "docx→pdf", "image→image", "csv→json"]` in error |
| Deterministic output for same input | Reproducibility matters for testing | LOW | No timestamps or random elements in output unless requested |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| HTML → PDF with CSS/JS rendering | Most html-to-pdf tools use wkhtmltopdf (outdated); Playwright renders modern CSS correctly | LOW | Playwright is already in the stack from scraping API. Use `page.pdf()`. |
| Image conversion: format + resize in one call | Avoid two round-trips for "resize this JPEG to 800px and convert to WebP" | LOW | Pillow handles format conversion and resize in one operation. Parameters: `width`, `height`, `format`, `quality`. |
| CSV → JSON with header detection | Callers shouldn't have to specify column names — detect from first row | LOW | Python `csv.DictReader` does this automatically. |
| PDF page size / margin params for HTML→PDF | Agents generating PDFs for specific paper sizes (A4, Letter) need this | LOW | Playwright `page.pdf()` `format`, `margin` parameters. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| PDF → docx / PDF → editable formats | "Convert this PDF to Word" | Reverse-engineering PDF layout is extremely hard; results are poor; introduces heavyweight OCR dependency | PDF text extraction already exists as `x402_pdf_extract`. That's the right tool. |
| Video conversion / compression | "Convert this MP4 to WebM" | FFmpeg adds 100MB+ to Railway container; runtime is long; cost model doesn't fit | Out of scope. Audio transcription is a separate API. |
| Spreadsheet (xlsx) → anything | Excel parsing is complex (formulas, merged cells, multiple sheets) | openpyxl has good coverage but edge cases are many; scope creep | CSV is the normalized form. Export to CSV first. |
| Batch conversion (array of files) | "Convert 50 files at once" | Single-request timeout doesn't allow it; billing model breaks | Caller loops; each file is one API call |
| Font embedding / print fidelity for docx→pdf | "My brand fonts must appear" | Font licensing + system font availability on Railway container | Use system fonts; document limitation. Good enough for 95% of cases. |

### Parameter Schema

```
input_url        string, required — URL of the file to convert (https:// only)
output_format    enum, required — Target format: "pdf", "png", "jpeg", "webp", "json"
                 Supported conversions:
                   html/htm → pdf
                   doc/docx/odt → pdf
                   png/jpeg/webp/gif/bmp → png|jpeg|webp
                   csv → json
width            integer, optional — For image resize: target width in px (preserves aspect ratio if height omitted)
height           integer, optional — For image resize: target height in px (preserves aspect ratio if width omitted)
quality          integer, optional — For JPEG/WebP output: quality 1-100 (default: 85)
page_format      enum("A4", "Letter", "Legal"), optional — For html→pdf: paper size (default: "A4")
page_margin      string, optional — For html→pdf: CSS margin shorthand (default: "1cm")
```

### Response Format

```json
{
  "input_url": "https://example.com/document.docx",
  "input_format": "docx",
  "output_format": "pdf",
  "content_type": "application/pdf",
  "size_bytes": 142857,
  "data": "<base64-encoded-pdf-contents>",
  "converted_at": "2026-03-12T00:00:00Z"
}
```

### Edge Cases

- **Unsupported input format** — return error listing supported conversions, not a generic 500
- **Protected / password-locked DOCX** — LibreOffice will fail; surface a clear error
- **HTML with external resources** — Playwright loads them (CSS, images, fonts); if the target page has blocking scripts, use a timeout
- **Very wide/tall images** — cap output dimensions at 8000x8000 to prevent memory exhaustion
- **CSV with inconsistent columns** — rows with more/fewer columns than header; Python `csv.DictReader` with `restkey`/`restval` parameters handles this
- **CSV with BOM (UTF-8 BOM from Excel exports)** — strip BOM before parsing
- **Large DOCX → PDF** — LibreOffice conversion can take 10-30s for complex documents; use a generous timeout (45s) and document it

### Complexity: MEDIUM

Four different conversion pipelines with different dependencies:
- HTML→PDF: Playwright (already available, trivial)
- DOCX→PDF: LibreOffice headless on Railway container (need to add to Dockerfile; not trivial but well-documented)
- Image resize: Pillow (pip install, trivial)
- CSV→JSON: Python stdlib (trivial)

The complexity is the LibreOffice Dockerfile dependency. Consider shipping image resize + CSV→JSON + HTML→PDF first (all easy), then DOCX→PDF as a follow-up once the Dockerfile pattern is proven.

---

## API 5: Audio Transcription

### How It Works

Send an audio file URL. The API downloads the file, runs MLX Whisper on the home Mac server (10.0.0.2), and returns the text transcript. Self-hosted — no per-minute charges to OpenAI or Deepgram.

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Audio URL → plain text transcript | The core output | LOW | MLX Whisper output is a dict with `text` key |
| Language detection (auto) | Most callers don't know the source language | LOW | MLX Whisper auto-detects; return detected language in response |
| Detected language in response | Agents use this for downstream processing (translation, etc.) | LOW | Whisper returns `language` in the result |
| Supported formats listed | mp3, mp4, wav, m4a, flac, ogg are all common | LOW | Whisper/ffmpeg handles all of these; document clearly |
| Processing time estimate / duration in response | Long files = long wait; callers need context | LOW | Return `audio_duration_seconds` and `processing_time_ms` |
| Clear size/duration limits | 10 minute audio = fine; 3 hour podcast = not | LOW | Cap at 25MB file size and 60 min duration; return error before processing |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Word-level timestamps | `[{"word": "Hello", "start": 0.0, "end": 0.5}]` — enables subtitle generation, search, and clip extraction | LOW | MLX Whisper `word_timestamps=True`. Optional parameter — adds to response size. |
| `language` hint parameter | Force a specific language when auto-detection would be wrong (accent, code-switching) | LOW | Pass through to Whisper `language` param. ISO 639-1 code. |
| Confidence score per segment | Callers can identify uncertain portions for human review | LOW | Whisper returns segment-level `no_speech_prob` — invert to get confidence |
| Model selection hint | `tiny`/`base`/`large` — speed vs accuracy tradeoff | MEDIUM | Home server has `whisper-large-v3-mlx` per MEMORY.md. Start with large only for simplicity; add model selection if there's demand for faster/cheaper tiers. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time / streaming transcription | "Transcribe as I speak" | Requires WebSocket or SSE; stateless HTTP doesn't fit; home server would need always-open connections | Submit audio file after recording; not real-time |
| Speaker diarization (who said what) | "Label each speaker" | Requires pyannote or similar — different model, significant additional complexity | Out of scope for v1.1. Assembly AI's differentiator — viable as v1.2. |
| Translation (audio → different language text) | Whisper actually supports this natively | Scope creep; different output schema | Whisper's `task=translate` is one line of code — could add as `translate_to` parameter, but leave for v1.2 |
| Punctuation restoration | "Add punctuation to the raw Whisper output" | Whisper large-v3 already includes punctuation when it detects natural speech patterns | Not a separate feature — just use whisper-large-v3-mlx and it's included |
| Batch transcription (multiple files) | "Transcribe 20 recordings" | Home server is single-GPU; concurrent jobs would queue; billing model doesn't communicate wait times | Sequential calls; each file is one API call |

### Parameter Schema

```
audio_url        string, required — URL of audio file to transcribe (https://, must be publicly accessible)
language         string, optional — ISO 639-1 language code hint (e.g., "en", "es", "fr"). Auto-detected if omitted.
word_timestamps  boolean, optional — Include word-level timing in response (default: false)
```

### Response Format

```json
{
  "transcript": "Hello, this is a test transcription of some audio content.",
  "language": "en",
  "language_probability": 0.99,
  "audio_duration_seconds": 12.4,
  "processing_time_ms": 3200,
  "segments": [
    {
      "start": 0.0,
      "end": 4.2,
      "text": "Hello, this is a test transcription",
      "confidence": 0.97
    }
  ],
  "words": [
    { "word": "Hello", "start": 0.0, "end": 0.48 },
    { "word": "this", "start": 0.52, "end": 0.72 }
  ]
}
```

Note: `words` field is only present when `word_timestamps: true`.

### Edge Cases

- **Non-public audio URL** — HTTP 403/401 on download; surface clearly ("audio URL is not publicly accessible")
- **Unsupported audio format** — ffmpeg converts most things before Whisper; but exotic formats may fail — return format as part of error message
- **Silent audio / music-only** — Whisper returns empty or near-empty transcript; return it as-is with `no_speech_detected: true` flag when `no_speech_prob > 0.7`
- **Very short audio (<1s)** — Whisper may return garbage; validate duration after download, reject < 0.5s
- **Home server offline** — Railway API is always up; transcription service on 10.0.0.2 may not be. Return a specific `service_unavailable` error distinct from generic errors, so agents know to retry later.
- **Concurrent requests** — Home server processes one at a time; queue requests or return `503 Service Unavailable` when busy. A simple file-lock mechanism is sufficient.
- **Audio URL behind redirect chains** — follow redirects on download (requests `allow_redirects=True`)
- **Free test endpoint** — use a short (< 5s) public audio file; same file every time, cached output

### Infrastructure Notes

- **Hosting:** Home Mac server at 10.0.0.2, accessible from Railway via local network or VPN. The Railway API service calls home server on transcription requests.
- **MLX Whisper model:** `whisper-large-v3-mlx` per MEMORY.md — already installed and used for voice notes
- **Architecture:** Railway FastAPI service acts as a proxy + validator; actual Whisper processing happens on the home server. Alternatively, run the full FastAPI service on the home server and expose via nginx — simpler, avoids Railway-to-home latency.
- **Recommended:** Run the transcription API service directly on the home Mac (Python/FastAPI + MLX Whisper), expose via nginx on a port, and configure x402 on that service. Railway is not needed for this API.

### Complexity: MEDIUM

MLX Whisper is already installed and tested per MEMORY.md voice notes pipeline. The complexity is the deployment architecture: home server FastAPI service + nginx + x402 integration. The actual Whisper code is 5 lines. The tricky parts are: concurrent request handling, the home-server-down scenario, and file download error handling.

---

## Cross-API Feature Dependencies

```
[Web Scraping API]
    └──uses──> [Playwright] (shared with File Conversion HTML→PDF)
    └──can complement──> [Web Search API] (search → scrape results pattern)

[File Conversion API (HTML→PDF)]
    └──shares Playwright with──> [Web Scraping API]

[File Conversion API (DOCX→PDF)]
    └──requires──> [LibreOffice in Railway Dockerfile]

[Audio Transcription API]
    └──requires──> [Home server (10.0.0.2) with MLX Whisper running]
    └──independent of──> [Railway] (or runs on home server directly)

[Web Search API]
    └──depends on──> [Tavily API key] (env var on Railway)
    └──can pipeline into──> [Web Scraping API] (search → get URLs → scrape)

[Email Sending API]
    └──depends on──> [Resend API key] (env var on Railway)
    └──independent of all other APIs]
```

### Dependency Notes

- **Playwright is already in the stack** (web scraping) — HTML→PDF conversion gets it for free. Deploy web scraping and file conversion as one Railway service or as services that share the same Playwright-enabled Docker image.
- **LibreOffice is the only new system dependency** — adds ~300MB to Docker image. Isolate DOCX→PDF to its own Railway service if image size is a concern, or ship image/CSV/HTML→PDF first and add DOCX→PDF later.
- **Audio transcription is the only non-Railway API** — it has a fundamentally different deployment model. Treat it as a separate integration from the other four Railway services.
- **Email and Search are the cleanest** — both are thin wrappers over third-party APIs (Resend, Tavily). Lowest risk, fastest to ship.

---

## MVP Definition

### Ship First (Lowest Risk, Highest Value)

- [ ] Email Sending — trivial backend, Resend SDK, huge agent utility, LOW complexity
- [ ] Web Search — Tavily SDK, thin wrapper, already designed for agents, LOW complexity
- [ ] Web Scraping — Playwright already planned, MEDIUM complexity but strong utility
- [ ] File Conversion (image resize + CSV→JSON + HTML→PDF only) — skip DOCX→PDF for v1.1
- [ ] Audio Transcription — MEDIUM complexity, unique (self-hosted) differentiator, but fragile home server dependency

### Defer to v1.2

- [ ] DOCX→PDF conversion — LibreOffice Dockerfile complexity; not blocking the other conversions
- [ ] Speaker diarization for transcription — separate model, significant work
- [ ] Structured JSON extraction (LLM-schema) for web scraping — expensive, requires LLM call per scrape
- [ ] Whisper model selection (tiny/base vs large) — expose after basic flow is validated

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Email sending (basic) | HIGH | LOW | P1 |
| Web search (Tavily) | HIGH | LOW | P1 |
| Web scraping (URL→markdown) | HIGH | MEDIUM | P1 |
| Image resize (Pillow) | MEDIUM | LOW | P1 |
| CSV→JSON | MEDIUM | LOW | P1 |
| HTML→PDF (Playwright) | HIGH | LOW | P1 |
| Audio transcription (URL→text) | HIGH | MEDIUM | P1 |
| Word-level timestamps | MEDIUM | LOW | P2 |
| `include_answer` for search | HIGH | LOW | P2 |
| `only_main_content` scraping | HIGH | LOW | P2 |
| Table extraction in scraping | MEDIUM | MEDIUM | P2 |
| `wait_for` selector in scraping | MEDIUM | LOW | P2 |
| DOCX→PDF (LibreOffice) | MEDIUM | MEDIUM | P2 |
| Email CC/BCC/reply-to | MEDIUM | LOW | P2 |
| Language hint for transcription | LOW | LOW | P2 |
| Email idempotency key | LOW | LOW | P3 |
| Search domain filtering | LOW | LOW | P3 |
| Search advanced depth tier | LOW | LOW | P3 |
| Speaker diarization | LOW | HIGH | P3 |
| Whisper model selection | LOW | MEDIUM | P3 |
| CSV multi-sheet / Excel (xlsx) | LOW | MEDIUM | P3 |

---

## Competitor Feature Analysis

| Feature | Firecrawl (scraping) | Tavily (search) | Deepgram/AssemblyAI (transcription) | ConvertAPI/CloudConvert (conversion) | Resend (email) | Our Approach |
|---------|--------------|--------------|--------------|--------------|--------------|--------------|
| Core output | Markdown + structured JSON | LLM-ready snippets + answer | Text + timestamps + speaker labels | Many formats, job-based | Transactional email | Focused subset: what agents actually need |
| Pricing model | Per-page credits, $16+/month | Per-query credits, free tier 1k/month | Per-minute audio | Per-conversion, subscription | Per-email, free tier 100/day | Per-call micropayment via x402 — no subscription |
| Auth | API key header | API key header | API key header | API key + secret | API key header | USDC micropayment (x402) |
| Free tier | 500 credits/month | 1,000 requests | None (trial only) | Limited free | 100 emails/day | Free test endpoint with fixture data |
| LLM-optimized output | Yes (markdown, clean text) | Yes (by design) | Partial | No | N/A | Yes — markdown first, clean schemas |
| Self-hosted option | Yes (complex) | No | No | No | No | Transcription is self-hosted on home Mac |
| Multi-step workflows | Crawl API | No | No | Job-based batching | No | Composable tools — agent chains calls |
| Agent-callable via MCP | Yes (Firecrawl MCP) | Yes (Tavily MCP) | No | No | No | Native — every tool is an MCP tool |

---

## Sources

- Firecrawl scrape endpoint documentation: [docs.firecrawl.dev/api-reference/endpoint/scrape](https://docs.firecrawl.dev/api-reference/endpoint/scrape)
- Firecrawl scrape tutorial: [firecrawl.dev/blog/mastering-firecrawl-scrape-endpoint](https://www.firecrawl.dev/blog/mastering-firecrawl-scrape-endpoint)
- Resend API reference: [resend.com/docs/api-reference/emails/send-email](https://resend.com/docs/api-reference/emails/send-email)
- Tavily pricing and credits: [docs.tavily.com/documentation/api-credits](https://docs.tavily.com/documentation/api-credits)
- Tavily getting started: [blog.tavily.com/getting-started-with-the-tavily-search-api](https://blog.tavily.com/getting-started-with-the-tavily-search-api)
- Brave Search API parameters: [api-dashboard.search.brave.com/app/documentation/web-search/query](https://api-dashboard.search.brave.com/app/documentation/web-search/query)
- Brave vs Tavily vs SerpAPI comparison: [firecrawl.dev/blog/top_web_search_api_2025](https://www.firecrawl.dev/blog/top_web_search_api_2025)
- Deepgram vs AssemblyAI comparison: [deepgram.com/learn/assemblyai-vs-deepgram](https://deepgram.com/learn/assemblyai-vs-deepgram)
- MLX Whisper README: [github.com/ml-explore/mlx-examples/blob/main/whisper/README.md](https://github.com/ml-explore/mlx-examples/blob/main/whisper/README.md)
- MLX Whisper PyPI: [pypi.org/project/mlx-whisper](https://pypi.org/project/mlx-whisper/)
- ConvertAPI and file conversion landscape: [convertapi.com](https://www.convertapi.com/)
- CloudConvert file conversion API: [cloudconvert.com/apis/file-conversion](https://cloudconvert.com/apis/file-conversion)
- Existing x402 MCP Server codebase: `/Users/jameswisdom/projects/x402-mcp-server/`
- PROJECT.md (v1.1 milestone context)

---
*Feature research for: v1.1 universal utility APIs — web scraping, email sending, web search, file conversion, audio transcription*
*Researched: 2026-03-12*
