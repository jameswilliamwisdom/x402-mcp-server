"""Payment replay resistance test.

Structural verification that a used payment header cannot be replayed against
a paid endpoint. Bismuth relies on the facilitator (Daydreams) enforcing
nonce uniqueness at the on-chain settlement layer, and the middleware
enforcing state.payment_payload gate at request time.

This is a live integration test against a running server. It does NOT sign
a real payment (that requires a funded wallet + signer); it verifies the
NEGATIVE path — that requests without a valid X-PAYMENT return 402, and
that fabricated / malformed payloads never succeed at the paid handler.

Run against a local dev server:
    PAY_TO_ADDRESS=0x... uvicorn main:app --port 8321 &
    pytest test_payment_replay.py -v

Or against staging by setting BASE_URL=https://staging....
"""

import os
import base64
import json
import time

import pytest
import httpx


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8321")


def _post_scrape(headers: dict | None = None) -> httpx.Response:
    return httpx.post(
        f"{BASE_URL}/scrape",
        json={"url": "https://example.com"},
        headers=headers or {},
        timeout=10.0,
    )


def test_scrape_without_payment_returns_402():
    """Baseline: no X-PAYMENT header → 402 with payment-required challenge."""
    r = _post_scrape()
    assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text[:200]}"
    assert "payment-required" in r.headers, "no payment-required header in 402 response"


def test_scrape_challenge_is_v2_shape():
    """The 402 payment-required header decodes to a v2 payment challenge."""
    r = _post_scrape()
    assert r.status_code == 402
    raw = r.headers["payment-required"]
    decoded = json.loads(base64.b64decode(raw))
    assert decoded.get("x402Version") == 2, f"expected v2, got {decoded.get('x402Version')}"
    accepts = decoded.get("accepts", [])
    assert len(accepts) >= 1, "no accepts in challenge"
    a = accepts[0]
    assert a.get("scheme") == "exact", f"wrong scheme: {a.get('scheme')}"
    assert a.get("network") == "eip155:8453", f"wrong network: {a.get('network')}"
    assert a.get("amount") == "20000", f"wrong amount for $0.02 USDC: {a.get('amount')}"


def test_scrape_with_garbage_payment_header_still_returns_402():
    """A fabricated X-PAYMENT header does not bypass verification."""
    fake_payload = base64.b64encode(json.dumps({
        "x402Version": 2,
        "payload": {
            "authorization": {
                "from": "0x0000000000000000000000000000000000000000",
                "to": "0x6b21227Ca9Bb3590BB62ff60BA0EFbBf9Ba22ACC",
                "value": "20000",
                "validAfter": str(int(time.time())),
                "validBefore": str(int(time.time()) + 300),
                "nonce": "0x" + "00" * 32,
            },
            "signature": "0x" + "00" * 65,
        },
        "accepted": {
            "scheme": "exact",
            "network": "eip155:8453",
            "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "amount": "20000",
            "payTo": "0x6b21227Ca9Bb3590BB62ff60BA0EFbBf9Ba22ACC",
            "maxTimeoutSeconds": 300,
        },
    }).encode()).decode()

    r = _post_scrape(headers={"X-PAYMENT": fake_payload})
    # Facilitator should reject the zero-signature. Response could be 402
    # (retry with real payment) or 400 (malformed) — but NEVER 200.
    assert r.status_code != 200, (
        f"fabricated payment header MUST NOT reach the paid handler. "
        f"Got {r.status_code}: {r.text[:300]}"
    )


def test_scrape_replay_same_header_twice():
    """Replay resistance: reusing the SAME X-PAYMENT header twice must not
    succeed the second time even if the first succeeded.

    This test uses a garbage header so both attempts fail — but the important
    thing is that the second attempt does not return 200 due to any caching
    or short-circuit in the middleware.
    """
    fake_payload = base64.b64encode(json.dumps({
        "x402Version": 2,
        "payload": {
            "authorization": {
                "from": "0x0000000000000000000000000000000000000000",
                "to": "0x6b21227Ca9Bb3590BB62ff60BA0EFbBf9Ba22ACC",
                "value": "20000",
                "validAfter": str(int(time.time())),
                "validBefore": str(int(time.time()) + 300),
                "nonce": "0x" + "de" * 32,
            },
            "signature": "0x" + "00" * 65,
        },
        "accepted": {
            "scheme": "exact",
            "network": "eip155:8453",
            "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "amount": "20000",
            "payTo": "0x6b21227Ca9Bb3590BB62ff60BA0EFbBf9Ba22ACC",
            "maxTimeoutSeconds": 300,
        },
    }).encode()).decode()

    r1 = _post_scrape(headers={"X-PAYMENT": fake_payload})
    r2 = _post_scrape(headers={"X-PAYMENT": fake_payload})
    assert r1.status_code != 200
    assert r2.status_code != 200
    # Beyond both being non-200, both should be the same rejection type,
    # confirming the middleware does not treat the second attempt as different.
    assert r1.status_code == r2.status_code, (
        f"middleware treated two identical fabricated payloads differently: "
        f"{r1.status_code} vs {r2.status_code} — possible short-circuit bug"
    )


def test_head_scrape_returns_challenge_not_500():
    """HEAD on a paid endpoint must not crash the middleware."""
    r = httpx.head(f"{BASE_URL}/scrape", timeout=5.0)
    # Should be a 402 or 405 — never 500
    assert r.status_code in (402, 405), (
        f"HEAD /scrape returned {r.status_code}, expected 402 or 405: {r.text[:200]}"
    )
