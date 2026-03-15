"""
x402 Transcription API
Transcribe audio files via faster-whisper — accepts an audio URL, downloads,
checks size/duration limits, and transcribes with auto language detection.
Optional word-level timestamps. SSRF-protected. Gated behind x402 USDC payment.
"""

import os
import json
import socket
import ipaddress
import tempfile
import threading
import warnings
import logging
from typing import Optional
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from fastapi_x402 import init_x402, pay
from faster_whisper import WhisperModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import (
    MAX_AUDIO_BYTES,
    MAX_DURATION_SECONDS,
    WHISPER_MODEL,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_CPU_THREADS,
    PRICE_PER_REQUEST,
    FREE_ENDPOINT_RATE,
)


# =============================================================================
# Logger and Warnings
# =============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("x402-transcription")

# Suppress benign FP16 CPU warning — int8 mode triggers this on every load
warnings.filterwarnings("ignore", message="FP16 is not supported")


# =============================================================================
# Model Globals (set in lifespan)
# =============================================================================

model: Optional[WhisperModel] = None
_model_lock = threading.Lock()

ALLOWED_SCHEMES = {"http", "https"}


# =============================================================================
# SSRF Validation
# =============================================================================

def _assert_ip_public(ip) -> None:
    """Raise ValueError if the IP is in a blocked (non-public) range."""
    # Unwrap IPv4-mapped IPv6 (e.g. ::ffff:192.168.1.1) before checking
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        _assert_ip_public(ip.ipv4_mapped)
        return
    if (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_multicast or ip.is_reserved or ip.is_unspecified):
        raise ValueError(f"URL resolves to blocked IP range: {ip}")


def validate_url_for_ssrf(url: str) -> None:
    """Raises ValueError if the URL targets a private/internal resource.

    Uses getaddrinfo (not gethostbyname) to catch both IPv4 and IPv6 records.
    Checks ALL resolved addresses — not just the first.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Scheme '{parsed.scheme}' not allowed; only http/https accepted")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("No hostname in URL")

    # Reject bare IP literals that are already private (before DNS resolution)
    try:
        direct_ip = ipaddress.ip_address(hostname)
        _assert_ip_public(direct_ip)
        return  # Valid public IP literal — no DNS needed
    except ValueError as e:
        # Either it's a private IP (re-raise) or not an IP literal (continue to DNS)
        if "blocked IP range" in str(e):
            raise
        # Not an IP literal — fall through to DNS resolution

    try:
        records = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValueError(f"DNS resolution failed: {e}")

    if not records:
        raise ValueError("DNS resolution returned no addresses")

    for record in records:
        ip_str = record[4][0].split("%")[0]  # Strip IPv6 scope ID
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError(f"Could not parse resolved IP: {ip_str!r}")
        _assert_ip_public(ip)


# =============================================================================
# Model Lifecycle (lifespan)
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load WhisperModel at startup via thread pool to avoid blocking the event loop."""
    global model
    logger.info(
        "Loading WhisperModel(%s, %s, %s, cpu_threads=%d)...",
        WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, WHISPER_CPU_THREADS,
    )
    model = await run_in_threadpool(
        lambda: WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
            cpu_threads=WHISPER_CPU_THREADS,
            num_workers=1,
        )
    )
    logger.info("WhisperModel loaded — ready to accept requests")
    yield
    # No teardown needed — model releases on process exit


# =============================================================================
# FastAPI App + Middleware
# =============================================================================

app = FastAPI(
    title="x402 Transcription API",
    description=(
        "Transcribe audio from any URL using faster-whisper. "
        "Auto language detection, optional word-level timestamps, 25MB/10min limits. "
        "Powered by x402 USDC payment (Base network)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# x402 payment middleware — added FIRST so it runs LAST (LIFO)
init_x402(app, network="base")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SSRFMiddleware(BaseHTTPMiddleware):
    """Pre-payment SSRF validation for POST /transcribe.

    Added AFTER init_x402() — LIFO ordering means this runs FIRST, before payment.
    SSRF-blocked requests return 400 with no charge to the caller.

    IMPORTANT: Path is "/transcribe" — verify this matches the POST endpoint name.
    """

    async def dispatch(self, request, call_next):
        # IMPORTANT: Path is "/transcribe" — NOT "/scrape" (Phase 5 copy-paste risk; see P13)
        if request.method == "POST" and request.url.path == "/transcribe":
            try:
                body_bytes = await request.body()
                body = json.loads(body_bytes)
                url = body.get("url", "")
                if url:
                    validate_url_for_ssrf(str(url))
            except ValueError as e:
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"SSRF validation failed: {e}"},
                )
            except (json.JSONDecodeError, Exception):
                # Let Pydantic handle malformed bodies
                pass
        return await call_next(request)


# SSRFMiddleware added LAST — LIFO means it runs FIRST (before payment check)
app.add_middleware(SSRFMiddleware)


# =============================================================================
# Rate Limiting (for free test endpoint)
# =============================================================================

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )


# =============================================================================
# Request Model
# =============================================================================

class TranscribeRequest(BaseModel):
    url: str                              # Audio file URL (TRANS-01)
    language: Optional[str] = None        # ISO 639-1 hint; None = auto-detect (TRANS-04)
    word_timestamps: bool = False          # Word-level timestamps (TRANS-03)


# =============================================================================
# SSRF Redirect Hook (httpx)
# =============================================================================

async def _validate_redirect_ssrf(response: httpx.Response) -> None:
    """Re-validate redirect target against SSRF rules on each hop.

    Prevents TOCTOU bypass: initial SSRF check passes, then a redirect points
    to a private IP. Called via event_hooks={"response": [_validate_redirect_ssrf]}.
    """
    if response.is_redirect:
        location = response.headers.get("location", "")
        if location:
            try:
                validate_url_for_ssrf(location)
            except ValueError as e:
                raise httpx.HTTPError(f"Redirect SSRF validation failed: {e}") from e


# =============================================================================
# Audio Download Function
# =============================================================================

async def download_audio_url(url: str) -> str:
    """Download audio from URL to a temp file with 25MB two-layer size cap.

    Layer 1: Content-Length header check (fast reject on declared size)
    Layer 2: Chunk accumulator (catches lying Content-Length headers)

    SSRF pre-flight is handled by SSRFMiddleware before this is called.
    Returns path to temp file. Caller is responsible for cleanup.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".audio") as tmp:
        tmp_path = tmp.name

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),  # longer for audio files
            follow_redirects=True,
            event_hooks={"response": [_validate_redirect_ssrf]},
        ) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                # Layer 1: Content-Length fast reject
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > MAX_AUDIO_BYTES:
                            raise ValueError(
                                f"Audio exceeds 25MB limit ({int(content_length) / 1024 / 1024:.1f}MB declared)"
                            )
                    except (ValueError, TypeError) as e:
                        if "25MB" in str(e):
                            raise
                        # Non-integer Content-Length — ignore and rely on Layer 2

                # Layer 2: Streaming chunk accumulator
                received = 0
                with open(tmp_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        received += len(chunk)
                        if received > MAX_AUDIO_BYTES:
                            raise ValueError(
                                f"Audio exceeds 25MB limit (stopped at {received / 1024 / 1024:.1f}MB)"
                            )
                        f.write(chunk)

        return tmp_path

    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


# =============================================================================
# Duration Check via PyAV
# =============================================================================

def get_audio_duration(tmp_path: str) -> float:
    """Return audio duration in seconds using PyAV (bundled with faster-whisper).

    No system ffmpeg required — PyAV reads container metadata directly.
    """
    import av
    container = av.open(tmp_path)
    duration = float(container.duration) / 1_000_000  # microseconds → seconds
    container.close()
    return duration


# =============================================================================
# Transcription (CPU-bound, serialized via lock)
# =============================================================================

def transcribe_audio(tmp_path: str, body: TranscribeRequest) -> dict:
    """Transcribe audio file using WhisperModel. Synchronous — call via run_in_threadpool.

    Threading.Lock serializes WhisperModel access — CTranslate2 is not thread-safe
    for concurrent use (see RESEARCH.md P4).

    CRITICAL: list(segments) MUST be called inside the lock block — segments is a
    lazy generator and transcription only runs when iterated (see RESEARCH.md P1).
    """
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
        # CRITICAL: force lazy generator evaluation INSIDE the lock
        segments_list = list(segments)

    transcript = " ".join(s.text.strip() for s in segments_list)

    result = {
        "transcript": transcript,
        "language": info.language,                              # TRANS-02
        "language_probability": round(info.language_probability, 3),  # TRANS-02
        "duration_seconds": round(info.duration, 2),
    }

    if body.word_timestamps:
        # TRANS-03: word-level timestamps
        result["timestamps"] = [
            {
                "word": w.word,
                "start": round(w.start, 3),
                "end": round(w.end, 3),
            }
            for seg in segments_list
            for w in (seg.words or [])
        ]
    else:
        # Default: segment-level timestamps
        result["segments"] = [
            {
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "text": s.text.strip(),
            }
            for s in segments_list
        ]

    return result


# =============================================================================
# Routes
# =============================================================================

@app.get("/")
async def root():
    """Service info and pricing."""
    return {
        "service": "x402-transcription-api",
        "price": PRICE_PER_REQUEST,
        "test": "/transcribe/test",
        "description": (
            "Transcribe audio from any URL — auto language detection, "
            "optional word-level timestamps, 25MB/10min limits."
        ),
        "endpoints": {
            "POST /transcribe": f"Transcribe audio URL (requires x402 USDC payment: {PRICE_PER_REQUEST})",
            "GET /transcribe/test": "Free fixture response — demonstrates full response schema",
            "GET /health": "Health check (model status)",
        },
        "limits": {
            "max_file_size": "25MB",
            "max_duration": "10 minutes",
            "model": WHISPER_MODEL,
            "compute": f"{WHISPER_DEVICE}/{WHISPER_COMPUTE_TYPE}",
        },
    }


@app.get("/health")
async def health():
    """Health check — always returns HTTP 200. Body includes model status."""
    return {
        "status": "healthy",
        "model": WHISPER_MODEL,
        "compute_type": WHISPER_COMPUTE_TYPE,
        "model_loaded": model is not None,
    }


@app.get("/transcribe/test")
@limiter.limit(FREE_ENDPOINT_RATE)
async def transcribe_test(request: Request):
    """Free test endpoint — returns fixture data (no model invocation, no payment required).

    Rate limited at 100 requests/hour per IP.
    Use POST /transcribe with x402 payment for real audio transcription.

    Response shape is identical to POST /transcribe — demonstrates full schema. (TRANS-06)
    """
    return {
        "transcript": "Hello world. This is a test transcription fixture from the x402 transcription API.",
        "language": "en",
        "language_probability": 0.998,
        "duration_seconds": 5.12,
        "segments": [
            {"start": 0.0, "end": 2.1, "text": "Hello world."},
            {"start": 2.1, "end": 5.12, "text": "This is a test transcription fixture from the x402 transcription API."},
        ],
    }


@app.post("/transcribe")
@pay(PRICE_PER_REQUEST)
async def transcribe(request: Request, body: TranscribeRequest):
    """Transcribe audio from a URL.

    Pipeline:
    1. SSRFMiddleware validates URL before this handler is reached
    2. Download audio via httpx streaming (25MB two-layer cap) (TRANS-01)
    3. Duration check via PyAV — reject if > 10 minutes (TRANS-05)
    4. Transcribe via faster-whisper small/int8/CPU (serialized via lock)
    5. Return transcript with language detection (TRANS-02) and timestamps

    Parameters:
    - url: Audio file URL (SSRF-validated, public URLs only)
    - language: ISO 639-1 language hint — omit for auto-detect (TRANS-04)
    - word_timestamps: True for word-level timestamps, False (default) for segments (TRANS-03)

    Returns:
    - transcript: Full text transcript
    - language: Detected language code (e.g. "en", "fr")
    - language_probability: Confidence in language detection (0.0–1.0)
    - duration_seconds: Audio duration
    - segments OR timestamps: Segment-level or word-level timing data

    Pricing: $0.05 USDC per transcription (Base network).
    Note: Payment is charged on download + probe; duration limit refusals are still charged.
    SSRF protection: private/loopback IPs rejected before payment.
    """
    tmp_path = None
    try:
        # Step 1: Download audio (streaming, 25MB two-layer cap)
        try:
            tmp_path = await download_audio_url(str(body.url))
        except ValueError as e:
            raise HTTPException(status_code=413, detail=str(e))
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Audio download failed: HTTP {e.response.status_code} from {body.url}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Audio download failed: {e}",
            )

        # Step 2: Duration check (run in thread pool — reads container metadata)
        try:
            duration = await run_in_threadpool(get_audio_duration, tmp_path)
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"Could not read audio duration: {e}",
            )

        if duration > MAX_DURATION_SECONDS:
            # TRANS-05: clear error message with exact duration and limit
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "duration_exceeded",
                    "detail": f"Audio is {duration / 60:.1f} minutes — exceeds 10-minute limit.",
                },
            )

        # Step 3: Transcribe (CPU-bound, serialized via _model_lock)
        if model is None:
            raise HTTPException(
                status_code=503,
                detail="Model unavailable — service is still starting up. Try again in a few seconds.",
            )

        try:
            result = await run_in_threadpool(transcribe_audio, tmp_path, body)
        except Exception as e:
            logger.error("Transcription failed for %s: %s", body.url, e)
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {e}",
            )

        return result

    finally:
        # Always clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
