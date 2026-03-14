# Phase 9: Audio Transcription API - Research

**Researched:** 2026-03-14
**Domain:** Self-hosted faster-whisper transcription + x402 payment gating + macOS process management
**Confidence:** HIGH (core stack and integration patterns verified; MEDIUM on Cloudflare Tunnel timeout behavior and temperature fallback memory specifics)
**Method:** MECE decomposition (3 dimensions: INTEGRATION, STACK, PITFALLS)

---

## Summary

Phase 9 is a FastAPI service running on the home Mac server (Intel x86_64, macOS Monterey) at port 8889. It accepts a JSON body containing an audio URL, downloads the file via streaming (25MB cap), checks duration via ffprobe/PyAV (10-minute limit), and transcribes via `faster-whisper` with `compute_type="int8"`. The response includes transcript text, detected language, language confidence, and optionally word-level or segment-level timestamps. Payment is gated via `fastapi-x402` (same pattern as all 4 Railway services), with a hand-rolled fallback if macOS compatibility issues arise. Public access is provided by Cloudflare Tunnel routing `transcribe.jameswisdom.ink` → `localhost:8889`. A launchd LaunchAgent plist with `KeepAlive` persists the service across reboots.

The recommended model is `small` (466MB disk, ~852MB RAM int8): 3.4% WER with full multilingual support, ~4x faster than `large` on CPU, and the most widely deployed CPU model in real-world production. Pricing recommendation is $0.05 per request — competitive with OpenAI's Whisper API ($0.006/min) while covering home server compute cost. The three most critical implementation details to get right are: (1) `list(segments)` must be called to force generator evaluation, (2) a `threading.Lock` must serialize WhisperModel access, and (3) `cpu_threads` must not exceed physical core count to avoid OOM.

All the hard infrastructure problems — SSRF validation, streaming download, process persistence, audio probing — are solved by prior phases or the OS. Phase 9 wires them together.

**Primary recommendation:** Use `WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)` loaded at FastAPI lifespan startup, serialized via `threading.Lock`, called from `run_in_threadpool`. Use `fastapi-x402>=0.1.8` with `init_x402(app, network="base")`. Point cloudflared config directly at `localhost:8889` (skip nginx in the tunnel path).

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Public Access**
- Cloudflare Tunnel (not port forwarding) — zero router config, no exposed home IP
- Public URL: `transcribe.jameswisdom.ink` (subdomain of existing Cloudflare-managed domain)
- `cloudflared` not yet installed on home server — install via Homebrew during setup
- Tunnel routes `transcribe.jameswisdom.ink` → `localhost:8889`

**Server Environment**
- Home server: 10.0.0.2, Intel x86_64, macOS Monterey — confirmed accurate
- Python 3 and Homebrew already installed
- Port 8889 is free and available
- ffmpeg status unknown — check and install via Homebrew if missing (`brew install ffmpeg`)
- `faster-whisper` with `compute_type="int8"` (Intel x86_64 — no MLX/Apple Silicon)

**Payment Middleware**
- Try `fastapi-x402` first (same as Railway services) — it may work fine on macOS
- If fastapi-x402 fails on macOS: fall back to hand-rolled middleware validating X-PAYMENT header against `https://x402.org/facilitator/verify`
- Same USDC wallet (PAY_TO_ADDRESS) as all Railway services — one wallet for the entire x402 network

**Audio Input & Limits**
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRANS-01 | Given an audio URL, return text transcript via faster-whisper on home server | STACK: `WhisperModel("small", device="cpu", compute_type="int8")` + `list(segments)` pattern; INTEGRATION: `httpx` streaming download → temp file → transcribe; file handling pipeline confirmed |
| TRANS-02 | Auto language detection with detected language in response | STACK: `info.language` + `info.language_probability` from `model.transcribe()` return value — available by default, no extra config needed; `small` model is fully multilingual |
| TRANS-03 | Optional word-level timestamps | STACK: `word_timestamps=True` param on `model.transcribe()` returns `segment.words[i].word/.start/.end/.probability`; recommended default `False` (opt-in, ~20-30% CPU overhead); PITFALLS: expose both modes via a `word_timestamps` bool parameter |
| TRANS-04 | Language hint parameter for known languages | STACK: `language` param on `model.transcribe()` — pass ISO 639-1 code (e.g., `"en"`, `"fr"`) or `None` for auto-detect; maps directly to API request body field |
| TRANS-05 | Size/duration limits (25MB / 10 min per CONTEXT.md) with clear error messages | INTEGRATION: two-layer 25MB streaming cap (Content-Length check + chunk accumulator); STACK: PyAV `av.open(path).duration / 1_000_000` (no system ffmpeg needed) OR `ffprobe` subprocess after download; PITFALLS: document that duration check occurs post-download post-payment |
| TRANS-06 | Free test endpoint with fixture data | STACK: `GET /transcribe/test` returning hardcoded fixture JSON — same shape as real response, no model invocation, no payment; same pattern as all prior phases |

</phase_requirements>

---

## Standard Stack

### Core Dependencies

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `faster-whisper` | 1.2.1 | Whisper transcription via CTranslate2, int8 CPU | 4x faster than openai/whisper; int8 CPU support; standard for self-hosted transcription |
| `fastapi` | >=0.100.0 | HTTP API framework | Same as all other x402 services in this project |
| `uvicorn[standard]` | >=0.23.0 | ASGI server | Same as all other x402 services |
| `httpx` | >=0.27.0 | Async audio URL download with streaming + size cap | Async-native, streaming chunks, supports SSRF redirect event_hooks |
| `slowapi` | >=0.1.9 | Rate limiting for free test endpoint | Same as all other x402 services |
| `pydantic` | >=2.0.0 | Request models | Same as all other x402 services |
| `fastapi-x402` | >=0.1.8 | x402 payment middleware | Identical to all 4 Railway services; proven on Base mainnet |

**Installation:**
```bash
pip install faster-whisper fastapi "uvicorn[standard]" pydantic fastapi-x402 httpx slowapi
```

### Python Environment

- Python 3.9+ required (faster-whisper supports 3.9, 3.10, 3.11)
- Use a venv in the service directory: `python3 -m venv .venv`
- The launchd plist must point to the venv Python binary (absolute path)
- Model cache: `~/.cache/huggingface/hub/` — `small` model is ~466MB on first download

### System Dependencies

- **ffmpeg/ffprobe**: Check if already installed via `which ffprobe`. If missing: `brew install ffmpeg`. Intel Homebrew path: `/usr/local/bin/ffprobe`.
- **Alternative**: Use PyAV (bundled with faster-whisper) for duration checking — no system ffmpeg needed. See Duration Check pattern in Code Examples.
- **cloudflared**: Not yet installed. Install via `brew install cloudflared` and configure tunnel during setup.
- **nginx**: Optional (LAN access only). Cloudflare Tunnel routes directly to `localhost:8889` — nginx is not in the public traffic path.

### x402 Package Decision

Two packages exist. This project uses `fastapi-x402` (jordo1138), NOT `x402[fastapi]` (coinbase v2):

- **`fastapi-x402>=0.1.8`**: API is `init_x402(app, network="base")` + `@pay("$0.05")`. Uses v1 header `X-PAYMENT`. Used in all existing Railway services.
- **`x402[fastapi]>=2.3.0`** (coinbase v2): Completely different API — `PaymentMiddlewareASGI` + CAIP-2 network IDs. Do not mix.

Pin `fastapi-x402>=0.1.8` explicitly in `requirements.txt`. Do not install bare `x402` alongside it.

### Model Selection (Recommended: `small`)

| Model | Disk | RAM (int8 CPU) | WER | Notes |
|-------|------|----------------|-----|-------|
| `small` | 466MB | ~852MB | 3.4% | **Recommended** — best speed/quality tradeoff for CPU pay-per-use |
| `medium` | 1.5GB | ~2.1GB | 2.9% | Fallback if accuracy is priority |
| `large-v3-turbo` | 1.6GB | ~2.3GB | 2.5% | Feasible but slow on Intel |
| `distil-large-v3` | ~1.5GB | ~2.0GB | ~9.7% | English-only — ruled out for multilingual API |

`small` rationale: 3.4% WER (excellent for pay-per-use), ~852MB RAM (leaves headroom), full multilingual, ~45-90s for 5-minute audio on Intel int8, most widely deployed CPU model in production code.

### USDC Pricing (Recommended: $0.05)

$0.05 per request. Rationale: 50-100s CPU time for 5-min audio; OpenAI Whisper API charges $0.006/min ($0.03 for 5 min); $0.05 is competitive while covering home server cost. Effective rate: $0.005/min for 10-min file.

---

## Architecture Patterns

### Request Processing Pipeline

```
POST /transcribe
  1. SSRFMiddleware (pre-flight) — validates URL against private IP ranges
  2. x402 payment middleware — checks X-PAYMENT header, returns 402 if absent
  3. Route handler (sync def → runs in thread pool automatically)
     a. Download audio via httpx streaming → temp file (25MB cap, two-layer check)
     b. Duration check via PyAV or ffprobe (reject if > 600s)
     c. Acquire threading.Lock
     d. model.transcribe(tmp_path, ...) → list(segments), info
     e. Release lock
     f. Delete temp file (finally block)
     g. Return transcript JSON
```

### Middleware Stack (LIFO Order)

```python
app = FastAPI(title="x402 Transcription API", lifespan=lifespan)

# Added FIRST → runs LAST (payment check — must be outermost)
init_x402(app, network="base")

# Added SECOND → runs SECOND
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)

# Added LAST → runs FIRST (SSRF pre-flight — must be innermost)
app.add_middleware(SSRFMiddleware)
```

### Model Lifecycle (lifespan pattern)

```python
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
from faster_whisper import WhisperModel
import threading

model: WhisperModel = None
_model_lock = threading.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    # Load model at startup — blocks event loop briefly via run_in_threadpool
    model = await run_in_threadpool(
        lambda: WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)
    )
    yield
    # No teardown needed

app = FastAPI(lifespan=lifespan, ...)
```

Model loads once at startup — prevents cold start timeout on first request. `cpu_threads=4` assumes 4 physical cores; verify with `sysctl -n hw.physicalcpu` on the server.

### Route Handler (sync def — thread pool routing)

```python
from fastapi import Request
from starlette.concurrency import run_in_threadpool

class TranscribeRequest(BaseModel):
    url: str
    language: Optional[str] = None        # ISO 639-1 hint; None = auto-detect (TRANS-04)
    word_timestamps: bool = False          # Optional word-level timestamps (TRANS-03)

@app.post("/transcribe")
@pay("$0.05")
async def transcribe(request: Request, body: TranscribeRequest):
    tmp_path = None
    try:
        # Download (streaming, 25MB cap)
        tmp_path = await download_audio_url(body.url)

        # Duration check (run in thread pool — I/O + CPU)
        duration = await run_in_threadpool(get_audio_duration, tmp_path)
        if duration > 600:
            raise HTTPException(422, detail={
                "error": "duration_exceeded",
                "detail": f"Audio is {duration/60:.1f} minutes — exceeds 10-minute limit."
            })

        # Transcribe (CPU-bound, serialized via lock)
        result = await run_in_threadpool(transcribe_audio, tmp_path, body)

        return result

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

def transcribe_audio(tmp_path: str, body: TranscribeRequest) -> dict:
    """CPU-bound. Called via run_in_threadpool."""
    with _model_lock:
        segments, info = model.transcribe(
            tmp_path,
            language=body.language,
            word_timestamps=body.word_timestamps,
            beam_size=1,
            best_of=1,
            temperature=0,
            vad_filter=True,
        )
        segments_list = list(segments)   # CRITICAL: forces generator evaluation

    text = " ".join(s.text.strip() for s in segments_list)

    response = {
        "transcript": text,
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration_seconds": round(info.duration, 2),
    }

    if body.word_timestamps:
        response["timestamps"] = [
            {"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)}
            for seg in segments_list
            for w in (seg.words or [])
        ]
    else:
        response["segments"] = [
            {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
            for s in segments_list
        ]

    return response
```

### Free Test Endpoint (TRANS-06)

```python
@app.get("/transcribe/test")
async def transcribe_test():
    return {
        "transcript": "Hello world. This is a test transcription fixture.",
        "language": "en",
        "language_probability": 0.999,
        "duration_seconds": 5.12,
        "segments": [
            {"start": 0.0, "end": 2.1, "text": "Hello world."},
            {"start": 2.1, "end": 5.12, "text": "This is a test transcription fixture."},
        ],
    }
```

### launchd LaunchAgent Plist

Location: `~/Library/LaunchAgents/com.x402.transcription.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.x402.transcription</string>

    <key>ProgramArguments</key>
    <array>
        <string>/path/to/x402-transcription-api/.venv/bin/uvicorn</string>
        <string>main:app</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8889</string>
        <string>--forwarded-allow-ips=*</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/path/to/x402-transcription-api</string>

    <key>KeepAlive</key>
    <true/>

    <key>RunAtLoad</key>
    <true/>

    <key>ThrottleInterval</key>
    <integer>30</integer>

    <key>StandardOutPath</key>
    <string>/tmp/com.x402.transcription.stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/com.x402.transcription.stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PAY_TO_ADDRESS</key>
        <string>FILL_IN_AT_DEPLOY</string>
        <key>CDP_API_KEY_ID</key>
        <string>FILL_IN_AT_DEPLOY</string>
        <key>CDP_API_KEY_SECRET</key>
        <string>FILL_IN_AT_DEPLOY</string>
    </dict>
</dict>
</plist>
```

Load/manage:
```bash
launchctl load ~/Library/LaunchAgents/com.x402.transcription.plist
launchctl unload ~/Library/LaunchAgents/com.x402.transcription.plist
launchctl list | grep x402
```

### Cloudflare Tunnel Configuration

Point directly at uvicorn (not nginx):

```yaml
# ~/.cloudflared/config.yml
tunnel: <TUNNEL-UUID>
credentials-file: /Users/<username>/.cloudflared/<TUNNEL-UUID>.json

originRequest:
  connectTimeout: 30s
  keepAliveTimeout: 90s
  tcpKeepAlive: 30s

ingress:
  - hostname: transcribe.jameswisdom.ink
    service: http://localhost:8889
  - service: http_status:404  # catch-all REQUIRED — tunnel won't start without it
```

Setup sequence:
```bash
brew install cloudflared
cloudflared tunnel login
cloudflared tunnel create transcription-api
cloudflared tunnel route dns transcription-api transcribe.jameswisdom.ink
cloudflared tunnel ingress validate
cloudflared tunnel run transcription-api   # test manually first
sudo cloudflared service install
# THEN: inspect plist and add "tunnel" + "run" args if missing (see Pitfalls)
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSRF validation on audio URL | Custom regex/domain blocklist | `validate_url_for_ssrf()` from Phase 5/6 — copy verbatim | DNS rebinding, IPv4-mapped IPv6, getaddrinfo vs gethostbyname — every custom implementation misses at least one bypass |
| Streaming size-limited download | `requests.get()` + `len(content)` | Phase 6's `download_file()` pattern with `httpx.stream()` + `aiter_bytes` accumulator | `Content-Length` is advisory; a server can stream unlimited bytes with a lying header |
| Audio duration detection | Parsing MP3/MP4/OGG header bytes manually | PyAV `av.open(path).duration / 1_000_000` (bundled) OR `subprocess.run(["ffprobe", ...])` | Audio container formats are complex; manual parsing misses edge cases |
| Process persistence on macOS | cron `@reboot`, supervisor, nohup+screen | launchd plist with `KeepAlive`, `ThrottleInterval`, `StandardErrorPath` | macOS's native process supervision — anything else fights the OS |
| HTTP request body parsing in middleware | Custom request body reader | `await request.body()` + `json.loads()` (Phase 5/6 pattern) | FastAPI consumes the body stream; `.body()` in middleware buffers it for downstream handler |
| Model thread safety | Per-request model instantiation (OOM) or lock-free concurrent access (corruption) | Single model instance + `threading.Lock` around `transcribe()` + `run_in_threadpool` | Model load is 2-5 seconds and ~1GB RAM; loading per request is catastrophic. CTranslate2 is not safe for concurrent use |
| Subprocess timeout with guaranteed kill | `signal.alarm()`, `Thread.join(timeout)` without kill | `concurrent.futures.Future.result(timeout=300)` for thread isolation | Python threads cannot be forcibly killed; this is the idiomatic timeout approach |
| Cloudflare Tunnel routing | Custom ngrok wrapper, SSH tunnel, port forwarding | `cloudflared tunnel` with named tunnel + DNS CNAME | Zero router config, persistent reconnect, free, TLS-terminated |

---

## Common Pitfalls

### P1: `segments` Is a Lazy Generator — Transcription Doesn't Run Until Iterated

`model.transcribe()` returns a lazy generator. Calling it and checking `info` without iterating `segments` produces no transcript. Transcription only runs when the generator is consumed.

```python
segments, info = model.transcribe(audio_path, ...)
segments_list = list(segments)   # MUST be inside the try block; this is when CPU work runs
```

**Warning sign:** Response returns immediately with empty transcript and no error.
**Confidence:** HIGH — documented in faster-whisper README and multiple deployment guides.

---

### P2: `cpu_threads` Exceeding Physical Core Count Causes OOM

Setting `cpu_threads` above the physical core count causes CTranslate2 to create more OS threads than cores can service. This keeps partially-processed audio buffers alive longer, growing peak RSS until OOM.

**Fix:** Check physical cores via `sysctl -n hw.physicalcpu`. Set `cpu_threads` to that value. `os.cpu_count() // 2` is a conservative default if hyperthreading is present.

**Warning sign:** Python process RSS grows steadily throughout a single long transcription.
**Confidence:** HIGH — confirmed by maintainer in GitHub issue #249.

---

### P3: `best_of=5` + Temperature Fallback Multiplies Memory

Default `best_of=5` can trigger up to 5 decoding passes on difficult audio. For CPU int8 inference on long audio, this 3-5x peak memory vs. single pass.

**Fix:** For a pay-per-use API where speed and memory predictability matter, use greedy decoding:
```python
segments, info = model.transcribe(audio_path, best_of=1, temperature=0, beam_size=1, ...)
```

**Warning sign:** Transcription of 5-minute file uses 3-4x expected memory.
**Confidence:** MEDIUM — community-reported, cross-referenced with temperature fallback mechanism.

---

### P4: WhisperModel Is Not Thread-Safe for Concurrent Requests

Concurrent calls to `model.transcribe()` on the same `WhisperModel` instance cause severe latency degradation and potential inference corruption. CTranslate2's internal KV cache and beam state are not isolated per call.

**Fix:** Serialize via `threading.Lock`:
```python
_model_lock = threading.Lock()

def transcribe_audio(tmp_path, ...):
    with _model_lock:
        segments, info = model.transcribe(tmp_path, ...)
        return list(segments), info
```

**Warning sign:** Concurrent requests return garbled or partial transcripts.
**Confidence:** HIGH — documented in GitHub issue #1419, maintainers confirm sequential design.

---

### P5: SSRF Validation TOCTOU — DNS Rebinding Between Check and Download

SSRF check resolves hostname at validation time. The actual httpx download performs an independent DNS resolution. An attacker with a controlled DNS server can return a public IP during validation and `127.0.0.1` during the actual download.

**Fix:** Use the Phase 6 pattern — `event_hooks={"response": [on_redirect]}` in the httpx client to re-validate each redirect hop against SSRF rules. The SSRFMiddleware provides a best-effort pre-flight guard.

**Confidence:** HIGH — active CVE category (DNS rebinding); Phase 6 pattern established.

---

### P6: `Content-Length` Can Be Spoofed — Streaming Size Check Is Mandatory

Checking only the `Content-Length` header allows a server to return a lying header and stream unbounded bytes.

**Fix:** Two-layer check — reject if `Content-Length` header exceeds limit (fast path), AND accumulate bytes during streaming and reject mid-stream:
```python
async for chunk in response.aiter_bytes(chunk_size=65536):
    received += len(chunk)
    if received > MAX_FILE_BYTES:
        raise ValueError(f"Exceeds 25MB limit (stopped at {received/1024/1024:.1f}MB)")
```

**Confidence:** HIGH — exact pattern already in Phase 6 `download_file()`.

---

### P7: ffprobe Not in PATH When Launched via launchd

`ffprobe` works in terminal but fails under launchd because launchd does not source shell profile. Intel Homebrew path (`/usr/local/bin`) is not in launchd's default PATH.

**Fix:** Set PATH explicitly in the plist EnvironmentVariables (`/usr/local/bin:/usr/bin:/bin`) and use absolute path in subprocess calls: `FFPROBE_PATH = "/usr/local/bin/ffprobe"`. Or bypass the problem entirely by using PyAV for duration checking (no subprocess needed).

**Confidence:** HIGH — #1 launchd pitfall for Homebrew tools.

---

### P8: launchd KeepAlive Crash Loop Silently Unloads the Service

Rapid crashes (< ThrottleInterval seconds apart) trigger launchd's backoff throttle, which eventually silently unloads the service. Without `ThrottleInterval` set, the service can vanish with no visible indication.

**Fix:** Always include `ThrottleInterval` (30 seconds) and log paths in the plist. Check `launchctl list | grep x402` if the service seems missing.

**Confidence:** HIGH — fundamental launchd behavior.

---

### P9: LaunchAgents Require User to Be Logged In

`~/Library/LaunchAgents/` plists only activate when the owning user has an active GUI session. After a reboot with no login, the service never starts.

**Fix:** Enable automatic login in System Preferences → Users & Groups for the home server user. Alternatively, move to `/Library/LaunchDaemons/` (system-level, requires root ownership and `sudo launchctl load`).

**Confidence:** HIGH — fundamental Apple launchd design.

---

### P10: cloudflared `service install` Plist Missing `tunnel run` Arguments

Known bug (GitHub issue #589, open since 2022, still present in 2025 releases): `sudo cloudflared service install` installs a plist that runs `cloudflared` with no subcommand. The service starts but never establishes a tunnel.

**Fix:** After `service install`, inspect `/Library/LaunchDaemons/com.cloudflare.cloudflared.plist` and verify `<string>tunnel</string><string>run</string>` are in `ProgramArguments`. If missing, add them manually before loading.

**Confidence:** MEDIUM (community-confirmed, known GitHub issue).

---

### P11: Cloudflare Tunnel 4-Minute Connection Reset on Long Transcriptions

Cloudflare Tunnel enforces connection timeouts that can trigger on slow origin responses. A 10-minute audio file may take 100-200 seconds to transcribe; longer audio can hit tunnel timeout before the response arrives.

**Fix:** Add `keepAliveTimeout: 90s` and `tcpKeepAlive: 30s` to `originRequest` in `~/.cloudflared/config.yml`. Validate with a real 10-minute audio file during testing.

**Confidence:** MEDIUM — documented in Cloudflare community forums; specific timeout values need experimental validation.

---

### P12: Subprocess Timeout Does Not Kill CTranslate2 Threads

When a 300-second timeout fires, Python cannot kill the underlying CTranslate2 C++ threads. A timed-out transcription will continue using CPU in the background until it finishes naturally.

**Fix:** Use `concurrent.futures.ThreadPoolExecutor` with `future.result(timeout=300)`. The lock is released and the response is returned; the background thread runs to completion (acceptable for low-traffic home server). Document this behavior.

**Confidence:** MEDIUM — based on Python threading model; CTranslate2 architecture.

---

### P13: SSRFMiddleware Path Hardcoded to Wrong Endpoint (Copy-Paste Risk)

Phase 5's SSRFMiddleware checks `request.url.path == "/scrape"`. Phase 6 added a comment about this exact mistake. If copied verbatim to Phase 9, SSRF attacks on `/transcribe` are not blocked.

**Fix:** Update path check to `"/transcribe"` and add explicit comment:
```python
# IMPORTANT: Path is "/transcribe" — verify this matches the POST endpoint name
if request.method == "POST" and request.url.path == "/transcribe":
```

**Confidence:** HIGH — documented in Phase 6 source code comment; high recurrence risk.

---

### P14: Hand-Rolled x402 Must Fail Closed on Facilitator Unavailability

If `fastapi-x402` fails on macOS and the hand-rolled fallback is used, a naive implementation might allow requests when the facilitator is unreachable. This creates a free bypass.

**Fix:** Treat any non-200 response, connection error, or timeout from the facilitator as a hard rejection (HTTP 503), not a pass-through.

**Note:** `x402.org/facilitator` is testnet-only. For Base mainnet, use CDP facilitator URL with CDP credentials.

**Confidence:** HIGH — security fundamental; confirmed in x402 security analysis by Halborn (2025).

---

### P15: Duration Check Occurs Post-Download Post-Payment

Audio duration cannot be determined from HTTP headers — it requires reading the file's container metadata. This means: download happens first, payment is charged, then the duration check may reject the file.

**Fix:** Return a clear error: `{"error": "duration_exceeded", "detail": "Audio is 12.3 minutes — exceeds 10-minute limit."}`. Document in API that payment is charged for the download + probe, not the transcription. No x402 refund mechanism exists.

**Confidence:** HIGH — fundamental property of audio container formats.

---

## Code Examples

### Complete Audio Download Function (httpx streaming, 25MB cap, SSRF-safe)

```python
import httpx
import tempfile
import os

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25MB

async def download_audio_url(url: str) -> str:
    """Download audio from URL to a temp file. Enforces 25MB size limit.
    SSRF pre-flight must be called before this function (handled by SSRFMiddleware).
    Returns path to temp file. Caller is responsible for cleanup.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".audio") as tmp:
        tmp_path = tmp.name

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            event_hooks={"response": [_validate_redirect_ssrf]}  # Phase 6 pattern
        ) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_AUDIO_BYTES:
                    raise ValueError(f"Audio exceeds 25MB ({content_length} bytes declared)")

                received = 0
                with open(tmp_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        received += len(chunk)
                        if received > MAX_AUDIO_BYTES:
                            raise ValueError(f"Audio exceeds 25MB (stopped at {received/1024/1024:.1f}MB)")
                        f.write(chunk)
        return tmp_path
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

### Duration Check via PyAV (no system ffmpeg needed)

```python
import av

def get_audio_duration(tmp_path: str) -> float:
    """Returns duration in seconds. PyAV is bundled with faster-whisper — no system ffmpeg needed."""
    container = av.open(tmp_path)
    duration = float(container.duration) / 1_000_000  # microseconds → seconds
    container.close()
    return duration
```

Alternative (ffprobe subprocess, if PyAV edge cases are a concern):
```python
import subprocess, json

FFPROBE_PATH = "/usr/local/bin/ffprobe"  # Intel macOS Homebrew path

def get_audio_duration_ffprobe(tmp_path: str) -> float:
    result = subprocess.run(
        [FFPROBE_PATH, "-v", "quiet", "-show_format", "-print_format", "json", tmp_path],
        capture_output=True, text=True, timeout=30
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])
```

### WhisperModel Configuration

```python
from faster_whisper import WhisperModel
import warnings

# Suppress benign FP16 warning on CPU
warnings.filterwarnings("ignore", message="FP16 is not supported")

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8",
    cpu_threads=4,    # Match physical core count: sysctl -n hw.physicalcpu
    num_workers=1,    # Single-worker for home server single-request serialization
)
```

### x402 Middleware Pattern (Primary — fastapi-x402)

```python
from fastapi_x402 import init_x402, pay

app = FastAPI(title="x402 Transcription API", version="1.0.0", lifespan=lifespan)

init_x402(app, network="base")                     # Added first → runs last (LIFO)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(SSRFMiddleware)                  # Added last → runs first (LIFO)

@app.post("/transcribe")
@pay("$0.05")
async def transcribe(request: Request, body: TranscribeRequest):
    ...
```

### Per-Wallet Address Extraction (for rate limiting)

```python
# From decoded_payment (same pattern as Phases 7/8)
decoded = request.state.decoded_payment
wallet = decoded.get("payload", {}).get("authorization", {}).get("from", "").lower()
```

---

## State of the Art

**faster-whisper** (SYSTRAN, v1.2.1, Oct 2025): The production standard for self-hosted CPU transcription. CTranslate2 backend provides 4x speedup over openai/whisper with int8 quantization. v1.1.0 changed output types from NamedTuple to dataclass — use `dataclasses.asdict()`, not `._asdict()`. v1.2.1 is the current stable release.

**Whisper model landscape**: `large-v3-turbo` (Oct 2024) achieves near-`large-v3` accuracy at half the parameters. `distil-large-v3` is English-only but significantly faster for English-only use cases. For a multilingual public API, `small` or `medium` remain the practical CPU choices.

**x402 ecosystem**: v2 SDK (coinbase, March 2026) uses CAIP-2 network identifiers and a new `PaymentMiddlewareASGI` pattern — completely different from `fastapi-x402` v1 used throughout this project. Migration is a future consideration; for now, `fastapi-x402>=0.1.8` is the stable choice.

**Cloudflare Tunnel**: Mature, production-grade. `cloudflared` v2025.x maintains the same config format. The `service install` plist bug is a known, longstanding issue with a straightforward fix.

**launchd**: macOS Monterey uses `launchctl bootout`/`bootstrap` syntax (in addition to legacy `load`/`unload`). `ThrottleInterval` and `StandardErrorPath` are essential for production-grade service management.

---

## Open Questions

1. **Physical core count on home server**: `sysctl -n hw.physicalcpu` must be run on the actual machine to set `cpu_threads` correctly. The plist example assumes 4 cores.

2. **fastapi-x402 macOS compatibility**: The CONTEXT.md notes uncertainty about whether `fastapi-x402` works on macOS (vs. Railway Linux). This should be the first thing tested after installation. The hand-rolled fallback is ready if needed.

3. **PyAV vs. ffprobe for duration**: PyAV (bundled) avoids a system dependency but may have edge cases with unusual container formats. If transcription failures occur on unusual audio, fall back to ffprobe subprocess.

4. **Cloudflare Tunnel timeout for 10-minute audio**: The PITFALLS dimension rates this MEDIUM confidence. Empirical testing with a real 10-minute audio file is needed to validate the `keepAliveTimeout: 90s` config is sufficient.

5. **LaunchAgent vs. LaunchDaemon**: The plist template uses `~/Library/LaunchAgents/` (user-level, requires login). If the Mac reboots without auto-login, the service won't start. Confirm automatic login is enabled on the home server, or move to `/Library/LaunchDaemons/`.

6. **nginx necessity**: The Specific Ideas in CONTEXT.md mention nginx, but research confirms it is not in the Cloudflare Tunnel → uvicorn path. Include nginx only if LAN access to port 80 is needed for testing.

---

## Coverage Audit

| Check | Status | Details |
|-------|--------|---------|
| Mutually Exclusive | PASS | All three dimensions agree on stack choices, model selection, and patterns. No conflicts found. INTEGRATION and STACK both recommend `fastapi-x402>=0.1.8` — confirmed agreement. |
| Collectively Exhaustive | PASS | All required sections populated: Summary, Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples. Optional sections populated: User Constraints, Phase Requirements, State of the Art, Open Questions. |
| Dimension Coverage | PASS | INTEGRATION findings: x402 pattern, httpx download, nginx config, cloudflared setup, plist flags. STACK findings: faster-whisper API, model selection, PyAV duration, launchd plist. PITFALLS findings: all 15 pitfalls integrated, Don't Hand-Roll table complete. |
| Requirement Coverage | PASS | TRANS-01 through TRANS-06 all mapped in Phase Requirements table with specific research support citations. |

---

## Sources

### Primary (HIGH confidence)
- `/Users/jameswisdom/projects/x402-mcp-server/x402-scraping-api/main.py` — Canonical `init_x402` + LIFO middleware pattern, SSRF redirect hook, per-wallet extraction
- `/Users/jameswisdom/projects/x402-mcp-server/x402-email-api/main.py` — `decoded_payment["payload"]["authorization"]["from"]` wallet extraction confirmed
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/STATE.md` — Accumulated decision: `fastapi-x402` for all services
- [faster-whisper PyPI v1.2.1](https://pypi.org/project/faster-whisper/) — latest version, Python requirements, PyAV bundled ffmpeg
- [faster-whisper GitHub SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) — WhisperModel API, compute_type, return value structure, dataclass breaking change
- [SYSTRAN/faster-whisper Issue #249](https://github.com/SYSTRAN/faster-whisper/issues/249) — OOM root cause: `cpu_threads` > physical cores (maintainer confirmed)
- [SYSTRAN/faster-whisper Issue #1419](https://github.com/SYSTRAN/faster-whisper/issues/1419) — Thread safety: sequential processing required
- Phase 6 `x402-conversion-api/main.py` — `download_file()` streaming accumulator, SSRFMiddleware copy-paste warning
- Phase 5 `x402-scraping-api/main.py` — `validate_url_for_ssrf()`, middleware LIFO ordering
- [Apple launchd documentation](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) — LaunchAgent vs LaunchDaemon behavior
- [launchd.info Tutorial](https://www.launchd.info/) — ThrottleInterval, KeepAlive semantics
- [Cloudflare Tunnel macOS service docs](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/as-a-service/macos/)
- [Cloudflare Tunnel config file docs](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/configuration-file/)
- [PyPI - fastapi-x402 0.1.8](https://www.piwheels.org/project/fastapi-x402/) — latest version confirmed
- [AceDataCloud/FacilitatorX402](https://github.com/AceDataCloud/FacilitatorX402) — facilitator /verify request/response schema
- [FastAPI behind-a-proxy docs](https://fastapi.tiangolo.com/advanced/behind-a-proxy/) — `--forwarded-allow-ips` flag
- [x402 Security Analysis — Halborn](https://www.halborn.com/blog/post/x402-explained-security-risks-and-controls-for-http-402-micropayments) — Fail-closed verification requirement

### Secondary (MEDIUM confidence)
- [faster-whisper GitHub releases v1.1.0-v1.2.1](https://github.com/SYSTRAN/faster-whisper/releases) — NamedTuple → dataclass breaking change
- [GitHub issue #279: slow CPU](https://github.com/SYSTRAN/faster-whisper/issues/279) — thread configuration, 18.5s for 2-min audio on i7
- [GitHub discussion #636: CPU utilization](https://github.com/SYSTRAN/faster-whisper/discussions/636) — thread diminishing returns
- [OpenWhispr: Whisper Model Sizes](https://openwhispr.com/blog/whisper-model-sizes-explained) — WER benchmarks, RAM per model
- [distil-whisper/distil-large-v3 Hugging Face](https://huggingface.co/distil-whisper/distil-large-v3) — English-only limitation
- [Cloudflare Community — Tunnel 4-minute reset](https://community.cloudflare.com/t/cloudflare-tunnel-resetting-upload-after-4-minutes/599191)
- [Cloudflare Community — Max upload size](https://community.cloudflare.com/t/max-upload-size/630925) — 100MB limit applies to uploads only
- [cloudflared GitHub issue #589](https://github.com/cloudflare/cloudflared/issues/589) — macOS launchd plist missing `tunnel run` bug
- [x402 v2 migration guide (CDP docs)](https://docs.cdp.coinbase.com/x402/migration-guide) — v1 `X-PAYMENT` → v2 `PAYMENT-SIGNATURE` distinction
- [x402 FAQ (CDP docs)](https://docs.cdp.coinbase.com/x402/support/faq) — x402.org facilitator is testnet-only
- [nginx formulae - Homebrew](https://formulae.brew.sh/formula/nginx) — macOS Homebrew nginx paths
- [DNS Rebinding SSRF Bypass — Clear Gate](https://www.clear-gate.com/blog/ssrf-with-dns-rebinding-2/)
- [HTTPX docs - Timeouts](https://www.python-httpx.org/advanced/timeouts/)

### Tertiary (LOW confidence)
- CPU benchmark "50-100s per 5min audio on Intel" — from CONTEXT.md (user's prior research; plausible given i7 benchmark of 18.5s/2min ≈ 45s/5min)
- [faster-whisper temperature fallback memory multiplication](https://forum.videohelp.com/threads/410865-How-I-use-whisper-faster-on-my-machine) — community-reported; not in official docs
- large-v3-turbo RAM "~2.3GB int8" — derived from parameter count + quantization math (no direct CPU measurement found)
- [cloudflared launchd fix 2025] — multiple community reports confirm plist bug persists; fix is the same XML edit

---

## Metadata

**Confidence breakdown:**
- INTEGRATION: HIGH (x402 pattern, httpx streaming, nginx config, cloudflared setup) / MEDIUM (cloudflared launchd plist bug)
- STACK: HIGH (faster-whisper API, model selection, launchd plist)
- PITFALLS: HIGH (most pitfalls) / MEDIUM (temperature fallback memory, cloudflare timeout, subprocess kill)
- **Overall: HIGH** — core implementation patterns are well-verified; MEDIUM items are edge cases with documented mitigations

**Research date:** 2026-03-14
**Valid until:** 2026-09 (faster-whisper API changes infrequently; x402 v2 SDK may be worth revisiting for v2 migration)
**Dimensions researched:** INTEGRATION, STACK, PITFALLS (3 of 3 returned)
