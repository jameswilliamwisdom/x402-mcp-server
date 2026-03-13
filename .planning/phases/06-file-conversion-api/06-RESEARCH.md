# Phase 6: File Conversion API — Research

**Researched:** 2026-03-12
**Domain:** File conversion microservice — Pillow (image), Python stdlib CSV, WeasyPrint (HTML→PDF); FastAPI on Railway
**Confidence:** HIGH (all three dimensions returned HIGH confidence; one MEDIUM finding on httpx redirect SSRF hook)
**Method:** MECE decomposition (3 dimensions: STACK, PATTERNS, PITFALLS)

---

## Summary

Phase 6 builds a new Railway service (`x402-conversion-api`) with a single `POST /convert` endpoint that handles three distinct file conversion operations under one Pydantic discriminated union. The pipeline is structurally identical across all three types: validate URL, download source file (10MB streaming limit), convert, base64-encode output, return JSON envelope. This uniformity makes a single endpoint the right design — it unifies payment gating, SSRF middleware, and test fixture under one path. Multi-endpoint design has no benefit here.

The stack is minimal compared to Phase 5: `python:3.11-slim` (not the 1.5GB Playwright image), `Pillow>=12.0.0` for image resize/reformat, Python stdlib `csv`+`json` for CSV-to-JSON (zero additional dependencies), and `WeasyPrint>=68.1` for HTML-to-PDF. The single most operationally risky component is WeasyPrint's dependency on a chain of GLib/GTK system libraries (`libgobject-2.0-0`, `libpango-1.0-0`, `libcairo2`, etc.) that do not exist in `python:3.11-slim` by default and are lazy-loaded at first conversion call — not at import or build time. This means a Docker build can succeed and a health check can pass while the service is silently broken. The mitigation is a confirmed apt package list and a build-time smoke test in the Dockerfile.

Security posture requires attention to two dimensions: SSRF on the file download URL (same `validate_url_for_ssrf()` pattern from Phase 5, plus redirect-chain re-validation via httpx event hooks) and WeasyPrint's CVE-2025-68616 (SSRF bypass via HTTP redirect in internal url_fetcher, fixed in WeasyPrint 68.0). Both are addressed by the pinned library versions and patterns documented here. All CPU-bound conversion operations (Pillow resize, WeasyPrint `write_pdf()`) must run in `run_in_threadpool` to avoid blocking the FastAPI event loop.

**Primary recommendation:** Build `x402-conversion-api` as a single-file `main.py` FastAPI service on `python:3.11-slim` with the confirmed apt layer, discriminated union request model, shared download pipeline, and `run_in_threadpool` for all sync conversion calls.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONV-01 | Image resize/reformat (Pillow) — input URL + target dimensions/format | `Pillow>=12.0.0` with `Image.resize()`, `Image.LANCZOS`, JPEG mode conversion, supported formats JPEG/PNG/WEBP/GIF/BMP/TIFF — fully covered by STACK + PATTERNS + PITFALLS |
| CONV-02 | CSV→JSON conversion (Python stdlib) | `csv.DictReader` + `csv.Sniffer` + `utf-8-sig` BOM handling — zero pip dependencies; fully covered by STACK + PITFALLS |
| CONV-03 | HTML→PDF conversion (WeasyPrint) | `WeasyPrint>=68.1` with `HTML(string=..., base_url=..., url_fetcher=safe_url_fetcher).write_pdf()` — fully covered by STACK + PATTERNS + PITFALLS |
| CONV-04 | SSRF protection on file fetch URLs | `validate_url_for_ssrf()` reused from Phase 5 + httpx redirect event hook re-validation + WeasyPrint `safe_url_fetcher` — fully covered by PATTERNS + PITFALLS |
| CONV-05 | Free test endpoint with fixture data | `GET /convert/test` with `slowapi` rate limit (100/hour), fixture.json returning 1x1 PNG base64 — fully covered by PATTERNS |

---

## Standard Stack

### Python Dependencies (`requirements.txt`)

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
fastapi-x402>=0.1.8
Pillow>=12.0.0
weasyprint>=68.1
httpx>=0.27.0
slowapi>=0.1.9
```

**Python stdlib (no pip install):** `csv`, `json`, `base64`, `tempfile`, `io`, `socket`, `ipaddress`, `os`, `logging`

**Not needed (unlike Phase 5):** `playwright`, `trafilatura`, `beautifulsoup4`, `lxml`, `pandas` — WeasyPrint handles its own HTML parsing.

### Library Version Rationale

| Library | Version | Why |
|---------|---------|-----|
| `Pillow` | `>=12.0.0` | Addresses CVE-2025-48379 (heap buffer overflow in DDS); `Image.ANTIALIAS` removed in 10.0 (use `Image.LANCZOS`); Python >=3.10 |
| `weasyprint` | `>=68.1` | CVE-2025-68616 (SSRF bypass via url_fetcher redirect) fixed in 68.0; CVE-2024-28184 (file attachment bypass) fixed in 61.2; Pango >=1.44.0 required |
| `httpx` | `>=0.27.0` | Async streaming download; event hooks for redirect SSRF re-validation; `aiter_bytes()` for chunk-by-chunk size enforcement |
| `fastapi-x402` | `>=0.1.8` | Project-wide payment standard; `init_x402`, `@pay` decorator |
| `slowapi` | `>=0.1.9` | Rate limiting on `/convert/test`; in-memory; no Redis needed |

### Docker Setup

**Base image: `python:3.11-slim`** (Debian bookworm, ~130MB). Do NOT use the Phase 5 Playwright image (~1.5GB) — no browser needed. Do NOT use `python:3.10-slim-buster` (Debian Buster ships Pango 1.42.x, below WeasyPrint's 1.44.0 minimum).

**Required apt packages** — install BEFORE `pip install`. WeasyPrint lazy-loads these at first conversion call (not at import), so missing packages pass `docker build` and health checks but crash on first POST:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libgobject-2.0-0 \
    libglib2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
```

`libgobject-2.0-0` / `libglib2.0-0` are the most commonly missing on Railway. `fonts-liberation` is required — without it, PDFs render as boxes/blanks.

**Build-time smoke test** — add AFTER `pip install`, catches missing C libs at build time:

```dockerfile
RUN python -c "from weasyprint import HTML; HTML(string='<p>test</p>').write_pdf()"
```

**Complete Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libgobject-2.0-0 \
    libglib2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Smoke test: catches missing system libs at build time (not first request)
RUN python -c "from weasyprint import HTML; HTML(string='<p>test</p>').write_pdf()"

COPY main.py .
COPY fixture.json .

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Shell form `sh -c '...'` is required for `${PORT}` expansion. Exec form treats `${PORT}` as a literal string.

**railway.toml:**

```toml
[deploy]
startCommand = "sh -c 'uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}'"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

`healthcheckTimeout = 30` (not 120 like Phase 5 — no browser startup delay).

### Project Structure

```
x402-conversion-api/
├── main.py              # FastAPI app, all routes, conversion logic, SSRF
├── requirements.txt
├── Dockerfile
├── railway.toml
├── .env                 # PAY_TO_ADDRESS, X402_NETWORK (gitignored)
└── fixture.json         # Hardcoded test response for GET /convert/test
```

Single-file `main.py` pattern consistent with Phase 5 and existing services.

---

## Architecture Patterns

### Single Endpoint with Pydantic Discriminated Union

Use `POST /convert` with a `type` field discriminating between `"image"`, `"csv"`, `"html_pdf"`. Do not create three separate endpoints — the pipeline (download → convert → base64 → return) is identical for all three. One endpoint means one `@pay` decorator, one SSRFMiddleware path check, one fixture endpoint.

```python
from __future__ import annotations
from typing import Annotated, Literal, Optional, Union
from pydantic import BaseModel, Field, UrlConstraints
from pydantic_core import Url

BoundedHttpUrl = Annotated[
    Url,
    UrlConstraints(allowed_schemes=["http", "https"], max_length=2048),
]

class ImageConvertRequest(BaseModel):
    type: Literal["image"]
    url: BoundedHttpUrl
    format: Literal["jpeg", "png", "webp", "gif"] = "jpeg"
    width: Optional[int] = Field(None, ge=1, le=8000)
    height: Optional[int] = Field(None, ge=1, le=8000)

class CsvConvertRequest(BaseModel):
    type: Literal["csv"]
    url: BoundedHttpUrl

class HtmlConvertRequest(BaseModel):
    type: Literal["html_pdf"]
    url: BoundedHttpUrl

ConvertRequest = Annotated[
    Union[ImageConvertRequest, CsvConvertRequest, HtmlConvertRequest],
    Field(discriminator="type"),
]
```

Invalid `type` values produce a Pydantic 422 validation error automatically — no manual dispatch guard needed.

### Response Envelope

All three conversion types return the same shape:

```python
# Success (HTTP 200)
{
    "success": True,
    "type": "image",           # echoes request type
    "mime_type": "image/jpeg",
    "data": "<base64>",
    "warnings": []
}

# Error (HTTP 200 with success=false — consistent with Phase 5)
{
    "success": False,
    "type": "image",
    "error": "size_limit_exceeded",
    "detail": "Source file is 14.2MB — exceeds 10MB limit.",
    "warnings": []
}
```

MIME type map:

```python
MIME_TYPES = {
    "jpeg": "image/jpeg",
    "png":  "image/png",
    "webp": "image/webp",
    "gif":  "image/gif",
    "csv":  "application/json",
    "html_pdf": "application/pdf",
}
```

### Async File Download with Streaming Size Enforcement

Shared by all three conversion types. Two-layer size check: Content-Length header fast path + mandatory streaming accumulator (handles servers that omit Content-Length):

```python
import httpx

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB

async def download_file(url: str) -> bytes:
    def on_redirect(response):
        location = response.headers.get("location", "")
        if location:
            validate_url_for_ssrf(location)  # Re-validate each redirect hop

    async with httpx.AsyncClient(
        follow_redirects=True,
        max_redirects=5,
        timeout=httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0),
        event_hooks={"response": [on_redirect]},
    ) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()

            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_FILE_BYTES:
                raise ValueError(
                    f"Source file is {int(content_length) / 1024 / 1024:.1f}MB"
                    f" — exceeds 10MB limit."
                )

            chunks = []
            received = 0
            async for chunk in response.aiter_bytes(chunk_size=65536):
                received += len(chunk)
                if received > MAX_FILE_BYTES:
                    raise ValueError(
                        f"Source file exceeds 10MB limit (stopped after "
                        f"{received / 1024 / 1024:.1f}MB downloaded)."
                    )
                chunks.append(chunk)

    return b"".join(chunks)
```

### TemporaryDirectory Cleanup Pattern

Use `tempfile.TemporaryDirectory` as a context manager in all converters. Guaranteed cleanup on exception. Each request gets a unique tmpdir — no cross-request collision.

```python
import tempfile, os

async def convert_html_to_pdf(file_bytes: bytes, source_url: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.pdf")
        html_string = file_bytes.decode("utf-8", errors="replace")
        doc = weasyprint.HTML(string=html_string, base_url=source_url,
                              url_fetcher=safe_url_fetcher)
        doc.write_pdf(out_path)
        with open(out_path, "rb") as f:
            return f.read()
```

Pillow can use `BytesIO` entirely in-memory but should still be called within a `with tempfile.TemporaryDirectory()` block for pattern consistency.

### run_in_threadpool for Sync Conversion Calls

Pillow and WeasyPrint are synchronous and CPU-bound. Calling them directly inside `async def` blocks the FastAPI event loop. Wrap all sync conversion logic with `run_in_threadpool`:

```python
from starlette.concurrency import run_in_threadpool

# Image conversion
output_bytes = await run_in_threadpool(sync_resize_image, file_bytes, body.format, body.width, body.height)

# WeasyPrint
output_bytes = await run_in_threadpool(sync_html_to_pdf, file_bytes, source_url)
```

`convert_csv_to_json` is in-memory stdlib and fast enough to call synchronously, but wrapping it is harmless and consistent.

### Unified Route Handler

```python
@app.post("/convert")
@pay("$0.02")
async def convert(request: Request, body: ConvertRequest):
    source_url = str(body.url)

    try:
        file_bytes = await download_file(source_url)
    except ValueError as e:
        return {"success": False, "type": body.type, "error": "download_error", "detail": str(e), "warnings": []}
    except httpx.HTTPStatusError as e:
        return {"success": False, "type": body.type, "error": "http_error", "detail": f"Source URL returned HTTP {e.response.status_code}.", "warnings": []}

    try:
        if body.type == "image":
            output_bytes = await run_in_threadpool(sync_convert_image, file_bytes, body.format, body.width, body.height)
            mime_type = MIME_TYPES[body.format]
        elif body.type == "csv":
            output_bytes = await run_in_threadpool(csv_to_json, file_bytes)
            mime_type = "application/json"
        elif body.type == "html_pdf":
            output_bytes = await run_in_threadpool(sync_html_to_pdf, file_bytes, source_url)
            mime_type = "application/pdf"
    except Exception as e:
        return {"success": False, "type": body.type, "error": "conversion_error", "detail": str(e), "warnings": []}

    # Output size guard before base64 encoding
    MAX_OUTPUT_BYTES = 8 * 1024 * 1024
    if len(output_bytes) > MAX_OUTPUT_BYTES:
        return {"success": False, "type": body.type, "error": "output_too_large",
                "detail": f"Output ({len(output_bytes) / 1024 / 1024:.1f}MB) exceeds 8MB limit.", "warnings": []}

    encoded = base64.b64encode(output_bytes).decode("ascii")
    return {"success": True, "type": body.type, "mime_type": mime_type, "data": encoded, "warnings": []}
```

### x402 + SSRF Middleware Ordering (LIFO)

```python
app = FastAPI(title="x402 Conversion API", version="1.0.0")

init_x402(app, network="base")            # Added first → runs last
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(SSRFMiddleware)         # Added last → runs first
```

SSRF fires before payment — blocked requests cost the caller nothing.

**SSRFMiddleware path update from Phase 5:** Change `"/scrape"` to `"/convert"`. That is the only required change.

```python
class SSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "POST" and request.url.path == "/convert":
            try:
                body_bytes = await request.body()
                body = json.loads(body_bytes)
                url = body.get("url", "")
                if url:
                    validate_url_for_ssrf(str(url))
            except ValueError as e:
                return JSONResponse(status_code=400, content={"detail": f"SSRF validation failed: {e}"})
            except (json.JSONDecodeError, Exception):
                pass
        return await call_next(request)
```

`validate_url_for_ssrf()` is copied verbatim from Phase 5 — same `socket.getaddrinfo()` + `ipaddress` stdlib pattern, same IPv4-mapped IPv6 unwrapping.

### Free Test Endpoint (CONV-05)

```python
@app.get("/convert/test")
@limiter.limit("100/hour")
async def convert_test(request: Request):
    return load_fixture()
```

Fixture (`fixture.json`):

```json
{
    "success": true,
    "type": "image",
    "mime_type": "image/png",
    "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "warnings": []
}
```

(The base64 string decodes to a valid 1x1 transparent PNG.)

### Standard Routes

```python
@app.get("/")
async def info():
    return {
        "service": "x402-conversion-api",
        "price": "$0.02",
        "test": "/convert/test",
        "description": "Convert files: image resize/reformat, CSV→JSON, HTML→PDF",
        "endpoints": {
            "POST /convert": "Convert a file (requires x402 USDC payment: $0.02)",
            "GET /convert/test": "Free fixture response",
            "GET /health": "Health check",
        },
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WeasyPrint SSRF on secondary fetches | Pre-flight URL validation only | `WeasyPrint>=68.0` + custom `url_fetcher` that calls `validate_url_for_ssrf()` on every redirect | CVE-2025-68616: pre-flight-only has TOCTOU bypass via HTTP redirect |
| File size enforcement | Read full response then check `len(data)` | `httpx` streaming with chunk accumulator aborting at `MAX_FILE_BYTES` | `Content-Length` is optional/spoofable; full download before check wastes RAM |
| Image mode conversion for JPEG | Manual pixel buffer manipulation | `Image.new("RGB", ...)` background + `paste()` with alpha mask | RGBA→JPEG is a known multi-step operation; naive `img.convert("RGB")` loses transparency incorrectly |
| CSV delimiter detection | Custom regex guesser | `csv.Sniffer().sniff(sample, delimiters=',;\t|')` | Python stdlib; handles quoted fields; falls back gracefully |
| UTF-8 BOM stripping in CSV | Check `content[:3] == b'\xef\xbb\xbf'` and slice | `content.decode('utf-8-sig')` | Built-in encoding handles both BOM and non-BOM cleanly |
| Thread isolation for Pillow/WeasyPrint | Custom process pool with IPC | `starlette.concurrency.run_in_threadpool()` | FastAPI idiomatic; no subprocess overhead |
| Decompression bomb protection | Check compressed file size only | `img.width * img.height > MAX_PIXELS` check before `img.load()` | Compressed size is irrelevant — a 50KB PNG can decompress to 500MB |
| Base64 size check | Encode first, then check string length | Check `len(output_bytes)` before `base64.b64encode()` | Saves ~33% memory; fails before the expensive encoding step |
| WeasyPrint system lib availability check | No check, discover at first request | Build-time smoke test: `RUN python -c "from weasyprint import HTML; HTML(string='<p>test</p>').write_pdf()"` | Catches missing apt packages at build time, not runtime |

---

## Common Pitfalls

### Critical: WeasyPrint C Libraries Pass Build, Crash at Runtime

WeasyPrint lazy-loads `libgobject-2.0-0`, `libcairo2`, `libpango-1.0-0` via `ctypes.util.find_library()` only when a conversion is attempted — not at `import weasyprint`. `docker build` succeeds, health check passes, first POST `/convert` with `type: "html_pdf"` throws `OSError: cannot load library 'libgobject-2.0-0'`. This is the top Railway + WeasyPrint failure mode (GitHub Issues #1772, #2221, #2461, Railway Help Station).

**Fix:** Full 12-package apt layer (see Docker Setup) + Dockerfile smoke test.

### Critical: SSRF Redirect-Chain Bypass During File Download

`validate_url_for_ssrf()` checks the original URL only. A server can respond with `301` to `http://169.254.169.254/latest/meta-data/`. httpx follows redirects automatically. The redirect destination bypasses SSRF validation.

**Fix:** httpx `event_hooks={"response": [on_redirect]}` with `validate_url_for_ssrf(location)` on each redirect hop. See `download_file()` pattern above.

### Critical: WeasyPrint CVE-2025-68616 — SSRF via url_fetcher Redirect

WeasyPrint makes its own HTTP requests for `<link>`, `<img>`, CSS `@import`. Pre-WeasyPrint-68.0, its internal urllib followed redirects without returning to developer validation (TOCTOU bypass). CVSS 7.5 High.

**Fix:** Pin `weasyprint>=68.1`. Implement `safe_url_fetcher` that calls `validate_url_for_ssrf()` on every URL WeasyPrint fetches.

### Pillow: Decompression Bomb (OOM Kill on Railway)

A 50KB PNG can decompress to 500MB of pixel data. `Image.open()` is lazy — pixel data loads on first access. Pillow's built-in `MAX_IMAGE_PIXELS` limit (~180MP) allows ~720MB RGBA images.

**Fix:** Check pixel count immediately after `Image.open()`, before `img.load()`:

```python
MAX_PIXELS = 50_000_000  # 50MP — safe for Railway 512MB tier

img = Image.open(BytesIO(file_bytes))
if img.width * img.height > MAX_PIXELS:
    raise ValueError(f"Image too large: {img.width}x{img.height} pixels")
```

Do not set `Image.MAX_IMAGE_PIXELS = None`.

### Pillow: RGBA → JPEG Silent Failure

`image.save(path, "JPEG")` on an RGBA image raises `OSError: cannot write mode RGBA as JPEG`. JPEG has no alpha channel. Naive `img.convert("RGB")` drops transparency by mapping it to black.

**Fix:** Composite onto white background before JPEG save:

```python
def prepare_for_jpeg(img):
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        return background
    if img.mode != "RGB":
        return img.convert("RGB")
    return img
```

### Pillow: `Image.ANTIALIAS` AttributeError

`Image.ANTIALIAS` was removed in Pillow 10.0.0. Always write `Image.LANCZOS`.

### CSV: BOM Prefix Corrupts First Column Header

Excel/Google Sheets CSV exports use UTF-8 with BOM (`\xef\xbb\xbf`). `file_bytes.decode("utf-8")` leaves `\ufeff` as prefix on the first key. All lookups against that field silently fail.

**Fix:** Always decode with `content.decode("utf-8-sig")` — handles both BOM and non-BOM. Fallback to `"latin-1"` for Windows ANSI exports.

### CSV: European Semicolon Delimiter

Default `csv.DictReader` uses comma. German/French locale exports use `;`. Entire file parses as one column.

**Fix:** Use `csv.Sniffer().sniff(sample[:4096], delimiters=',;\t|')` before constructing `DictReader`. Fall back to `csv.excel` (comma) on `csv.Error`.

### Content-Length Header is Optional

Do not rely solely on `Content-Length` for the 10MB limit. CDNs and chunked transfer encoding omit it. Enforce the limit during streaming accumulation (see `download_file()` pattern above).

### WeasyPrint Blocks the Event Loop

`HTML.write_pdf()` is synchronous and CPU-bound. Called directly inside `async def` it blocks all requests for the conversion duration (5–30 seconds for complex HTML). Same applies to Pillow operations.

**Fix:** `run_in_threadpool` for all Pillow and WeasyPrint calls.

### WeasyPrint: Blank or Box-Filled PDF

If `fonts-liberation` is not in the apt layer, `python:3.11-slim` has no system fonts. WeasyPrint renders `.notdef` glyphs (boxes) or blank pages — no exception raised.

**Fix:** `fonts-liberation` is included in the confirmed apt package list.

### WeasyPrint: Pango Version — Debian Buster Base Image

`python:3.10-slim-buster` ships Pango 1.42.x. WeasyPrint requires Pango >= 1.44.0. Text rendering fails at PDF generation, not at import.

**Fix:** Use `python:3.11-slim` (Debian bookworm, Pango 1.50.x).

### SSRFMiddleware Path — Copy-Paste Bug from Phase 5

Phase 5 SSRFMiddleware checks `request.url.path == "/scrape"`. If copied verbatim, all `/convert` requests skip SSRF validation silently.

**Fix:** Update path check to `"/convert"`. That is the only required change from the Phase 5 pattern.

### Base64 Output Size Bloat

10MB input → ~13.5MB base64 string. At peak, input bytes + output bytes + base64 string all live in memory simultaneously (~33MB+ for a 10MB file). The MCP layer may have response size limits.

**Fix:** Apply an 8MB output limit before base64 encoding: `if len(output_bytes) > 8 * 1024 * 1024: raise ...`. Check `len(output_bytes)` before encoding, not after.

### Pydantic Discriminated Union Requires `type` in Body

Callers sending `{"url": "...", "format": "png"}` without `"type"` get a 422 validation error with a confusing discriminator message.

**Fix:** Document `type` prominently in the OpenAPI endpoint description and in the `info()` route response. The fixture echoes `"type": "image"`.

---

## Code Examples

### Complete Pillow Image Converter

```python
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from typing import Optional

MAX_PIXELS = 50_000_000  # 50MP

def sync_convert_image(file_bytes: bytes, fmt: str,
                       width: Optional[int], height: Optional[int]) -> bytes:
    try:
        img = Image.open(BytesIO(file_bytes))
    except UnidentifiedImageError:
        raise ValueError("Not a recognized image format")

    if img.width * img.height > MAX_PIXELS:
        raise ValueError(f"Image too large: {img.width}x{img.height} pixels (max {MAX_PIXELS:,})")

    ALLOWED_INPUT_FORMATS = {"JPEG", "PNG", "WEBP", "GIF", "BMP", "TIFF"}
    if img.format not in ALLOWED_INPUT_FORMATS:
        raise ValueError(f"Unsupported input format: {img.format}")

    img.load()  # Force decode now so errors surface before further processing

    # Resize (preserves aspect ratio if only one dimension given)
    if width or height:
        orig_w, orig_h = img.size
        if width and not height:
            height = int(orig_h * width / orig_w)
        elif height and not width:
            width = int(orig_w * height / orig_h)
        img = img.resize((width, height), Image.LANCZOS)

    # JPEG mode conversion — composite transparency onto white
    if fmt.lower() in ("jpeg", "jpg") and img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        converted = img.convert("RGBA") if img.mode == "P" else img
        background.paste(converted, mask=converted.split()[-1] if "A" in converted.mode else None)
        img = background
    elif fmt.lower() in ("jpeg", "jpg") and img.mode != "RGB":
        img = img.convert("RGB")

    out = BytesIO()
    pillow_fmt = "JPEG" if fmt.lower() == "jpg" else fmt.upper()
    save_kwargs = {"optimize": True}
    if pillow_fmt == "JPEG":
        save_kwargs["quality"] = 85
    img.save(out, format=pillow_fmt, **save_kwargs)
    return out.getvalue()
```

### Complete CSV-to-JSON Converter

```python
import csv, json
from io import StringIO

def csv_to_json(file_bytes: bytes) -> bytes:
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel  # Fallback: comma-separated

    reader = csv.DictReader(StringIO(text), dialect=dialect)

    if reader.fieldnames is None:
        raise ValueError("CSV has no header row or is empty.")

    rows = list(reader)
    return json.dumps(rows, ensure_ascii=False).encode("utf-8")
```

### WeasyPrint HTML-to-PDF with SSRF url_fetcher

```python
import weasyprint
import tempfile, os
from weasyprint.urls import default_url_fetcher

def safe_url_fetcher(url):
    validate_url_for_ssrf(url)  # Raises ValueError on private/internal targets
    return default_url_fetcher(url)

def sync_html_to_pdf(file_bytes: bytes, source_url: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.pdf")
        html_string = file_bytes.decode("utf-8", errors="replace")
        doc = weasyprint.HTML(
            string=html_string,
            base_url=source_url,
            url_fetcher=safe_url_fetcher,
        )
        doc.write_pdf(out_path)
        with open(out_path, "rb") as f:
            return f.read()
```

### Base64 Output Guard and Encoding

```python
import base64

MAX_OUTPUT_BYTES = 8 * 1024 * 1024  # 8MB → ~10.7MB as base64

if len(output_bytes) > MAX_OUTPUT_BYTES:
    return {
        "success": False,
        "type": body.type,
        "error": "output_too_large",
        "detail": f"Output ({len(output_bytes) / 1024 / 1024:.1f}MB) exceeds 8MB limit.",
        "warnings": [],
    }

encoded = base64.b64encode(output_bytes).decode("ascii")
```

---

## State of the Art

| Old Approach | Current Approach | Changed | Impact |
|--------------|------------------|---------|--------|
| `wkhtmltopdf` for HTML→PDF | WeasyPrint 68.x | ~2018 | No Qt/webkit binary; pure Python + system libs; modern CSS support |
| `requests` for HTTP in FastAPI | `httpx.AsyncClient` | ~2021 | Native async; streaming; event hooks for redirect SSRF; per-phase timeout control |
| Cairo direct dep in WeasyPrint | Pango only (Cairo removed from WeasyPrint direct dep) | WeasyPrint 52.5 (2021) | Cairo still present transitively via Pango but not directly required |
| `Image.ANTIALIAS` in Pillow | `Image.LANCZOS` | Pillow 9.1.0 (2022) | `ANTIALIAS` removed in Pillow 10.0; `LANCZOS` is the renamed constant |
| `python:3.11-slim-bullseye` (Debian 11) | `python:3.11-slim` (Debian bookworm) | Docker Hub 2023 | Default tag now resolves to bookworm; Pango 1.50.x |

**Deprecated — do not use:**
- `wkhtmltopdf`: Deprecated WebKit fork, Qt binary, security issues
- `Image.ANTIALIAS`: Raises `AttributeError` in Pillow >=10.0
- `python:3.10-slim-buster`: Pango 1.42.x fails WeasyPrint
- `weasyprint<68.0`: CVE-2025-68616 (SSRF bypass)

---

## Open Questions

1. **WeasyPrint `url_fetcher` API in 68.1:** The `default_url_fetcher` import from `weasyprint.urls` is verified from docs but not tested against a live 68.1 install. Confirm the import path during implementation. (MEDIUM confidence)

2. **Railway response body size limits:** Base64-encoded 8MB PDF output ~10.7MB JSON response body. Railway's max response size is not documented. Empirically test with a large PDF during integration testing.

3. **WeasyPrint external asset SSRF for CSS/images in converted HTML:** `safe_url_fetcher` intercepts WeasyPrint's secondary fetches but may not handle all redirect scenarios within WeasyPrint's internal request pipeline for v1.1. Document as a known limitation; implement full redirect validation in v1.2 if needed.

4. **Memory footprint under concurrent load:** Pillow in-memory resizing peaks at input decompressed + resized + compressed output simultaneously (~3x the uncompressed pixel buffer). WeasyPrint holds the entire document in memory until `write_pdf()` completes. Under concurrent load, Railway's default 512MB container tier may be insufficient. Consider requesting 1GB.

---

## Coverage Audit

| Check | Status | Details |
|-------|--------|---------|
| Mutually Exclusive | PASS | All three dimensions agree on library choices, patterns, and security mitigations. No conflicting recommendations. STACK and PATTERNS both recommend single-file `main.py`; PATTERNS and PITFALLS both recommend `run_in_threadpool`; all three agree on the apt package list. |
| Collectively Exhaustive | PASS | All required sections (Summary, Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples) populated. Optional sections (Phase Requirements, State of the Art, Open Questions) also populated. |
| Dimension Coverage | PASS | STACK: stack, Docker, library APIs integrated. PATTERNS: discriminated union, response envelope, download pipeline, route handler, test endpoint integrated. PITFALLS: all 17 pitfalls integrated, Don't Hand-Roll table integrated. |
| Requirement Coverage | PASS | CONV-01 through CONV-05 each map to at least one finding in the Phase Requirements table. |

---

## Sources

### Primary (HIGH confidence)

- [PyPI: Pillow 12.1.1](https://pypi.org/project/Pillow/) — current version, Python >=3.10
- [Pillow Image module docs](https://pillow.readthedocs.io/en/stable/reference/Image.html) — `open()`, `resize()`, `save()`, `LANCZOS`, mode handling, `MAX_IMAGE_PIXELS`
- [Pillow image file formats docs](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) — JPEG/PNG/WEBP/GIF format strings, RGBA→JPEG error
- [PyPI: WeasyPrint 68.1](https://pypi.org/project/weasyprint/) — current version, Python >=3.10
- [WeasyPrint First Steps docs (v68.1)](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) — system dep list, Pango >=1.44.0, font warning
- [WeasyPrint API Reference](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html) — `HTML()` params, `write_pdf()` return type
- [GitHub Advisory GHSA-983w-rhvv-gwmv / CVE-2025-68616](https://github.com/advisories/GHSA-983w-rhvv-gwmv) — WeasyPrint SSRF bypass, fixed in 68.0
- [GitHub Advisory GHSA-35jj-wx47-4w8r / CVE-2024-28184](https://github.com/advisories/GHSA-35jj-wx47-4w8r) — WeasyPrint file attachment bypass, fixed in 61.2
- [Python stdlib — csv module](https://docs.python.org/3/library/csv.html) — `DictReader`, `Sniffer`, dialect
- [Python stdlib — tempfile](https://docs.python.org/3/library/tempfile.html) — `TemporaryDirectory` context manager guarantees
- [Python stdlib — base64](https://docs.python.org/3/library/base64.html) — `b64encode()` return type
- [httpx docs — async support](https://www.python-httpx.org/async/) — `AsyncClient`, streaming, `aiter_bytes()`
- [FastAPI docs — run_in_threadpool](https://fastapi.tiangolo.com/async/) — synchronous function execution in async handlers
- [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection) — formula injection attack vectors
- `/Users/jameswisdom/projects/x402-mcp-server/x402-scraping-api/main.py` — Phase 5 reference; SSRF pattern, middleware ordering, `@pay` decorator order, fixture pattern
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/phases/05-web-scraping-api/05-RESEARCH.md` — Phase 5 architecture research

### Secondary (MEDIUM confidence)

- [WeasyPrint GitHub Issues #2221, #2461](https://github.com/Kozea/WeasyPrint/issues/2221) — Railway `libgobject-2.0-0` missing; confirmed fix with apt packages
- [Railway Help Station — WeasyPrint gobject](https://station.railway.com/questions/weasyprint-dependency-gobject-2-0-0-in-355c0bf6) — Railway-confirmed fix
- [aquavitae/docker-weasyprint Dockerfile](https://github.com/aquavitae/docker-weasyprint/blob/master/Dockerfile) — confirms slim base image + apt approach
- [Pydantic v2 docs — discriminated union](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions) — `Annotated[Union[...], Field(discriminator="type")]`
- [rednafi.com — Disallow large file downloads](https://rednafi.com/python/disallow-large-file-download/) — streaming enforcement pattern with httpx
- [Python bug tracker Issue 7185](https://bugs.python.org/issue7185) — csv UTF-8 BOM confirmed stdlib behavior
- [Vulert — CVE-2025-48379 Pillow DDS overflow](https://vulert.com/vuln-db/pypi-pillow-194383) — confirms need for Pillow >=12.0.0

### Tertiary (LOW confidence)

- Railway `LD_LIBRARY_PATH` workaround for WeasyPrint gobject — workaround for incomplete Dockerfile; not the correct solution; prefer proper apt layer
- WeasyPrint `url_fetcher` exact import path in 68.1 — `from weasyprint.urls import default_url_fetcher` — from docs/community; not tested against live 68.1 install
- WeasyPrint memory accumulation on multiple `write_pdf()` calls — reported in community issues; not reproducible with deterministic case
- Railway response body size limits — not in official Railway docs; empirical testing required

---

## Metadata

**Confidence breakdown:**
- STACK: HIGH — PyPI pages, official docs, Phase 5 patterns confirmed
- Docker base image + apt packages: HIGH — WeasyPrint docs, aquavitae Dockerfile, Railway-specific GitHub issues with confirmed fixes
- Library APIs (Pillow, WeasyPrint, csv, httpx): HIGH — official docs for all; stable APIs
- Security CVEs (CVE-2025-68616, CVE-2024-28184, CVE-2025-48379): HIGH — GitHub Advisory Database verified
- PATTERNS: HIGH — Phase 5 reference implementation directly reusable
- PITFALLS: HIGH — documented failure modes with confirmed fixes (one MEDIUM: httpx redirect event hook not empirically tested with fastapi-x402)

**Research date:** 2026-03-12
**Valid until:** 2026-09-12 — WeasyPrint and Pillow patch frequently; verify no new CVEs before implementation if delayed past Q2 2026
**Dimensions researched:** STACK, PATTERNS, PITFALLS (3 of 3 completed)
