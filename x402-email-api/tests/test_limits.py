"""
Security review 2026-11-18: relay limits on the email service.

Run (from x402-email-api/):
      pip install -r requirements.txt pytest httpx
      pytest tests/
"""

import base64
import os
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

os.environ.setdefault("PAY_TO_ADDRESS", "0x0000000000000000000000000000000000000001")
os.environ.setdefault("RESEND_API_KEY", "test-not-a-real-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main  # noqa: E402

WALLET = "0xAbC0000000000000000000000000000000000001"


def request_from(wallet=WALLET):
    state = SimpleNamespace()
    if wallet is not None:
        state.payment_payload = SimpleNamespace(payload={"authorization": {"from": wallet}})
    return SimpleNamespace(state=state)


def email(**kw):
    base = {"to": "a@one.example", "subject": "hi", "body": "hello"}
    base.update(kw)
    return main.EmailRequest(**base)


@pytest.fixture(autouse=True)
def fresh_counters(monkeypatch):
    monkeypatch.setattr(main, "_wallet_counts", {})
    monkeypatch.setattr(main, "_wallet_domain_counts", {})
    monkeypatch.setattr(main, "_wallet_recipient_counts", {})
    monkeypatch.setattr(main, "_global_recipient_count", [0, None])
    sent = []
    monkeypatch.setattr(main, "_do_send", lambda body: sent.append(body) or {"id": f"msg-{len(sent)}"})
    return sent


# ── per-message caps ────────────────────────────────────────────────────

def test_normal_message_with_cc_and_bcc_is_accepted():
    msg = email(cc=["b@two.example"], bcc=["c@three.example"])
    assert msg.recipients() == ["a@one.example", "b@two.example", "c@three.example"]


def test_recipient_count_is_capped():
    many = [f"user{i}@domain{i}.example" for i in range(main.MAX_RECIPIENTS_PER_MESSAGE)]
    with pytest.raises(ValidationError, match="too many recipients"):
        email(cc=many)
    with pytest.raises(ValidationError, match="too many recipients"):
        email(cc=many[:3], bcc=many[3:6])


def test_duplicate_addresses_count_once():
    msg = email(cc=["A@One.example", "b@two.example"], bcc=["b@two.example"])
    assert len(msg.recipients()) == 2


def test_attachment_count_is_capped():
    att = {"filename": "a.txt", "content": base64.b64encode(b"x").decode()}
    email(attachments=[att] * main.MAX_ATTACHMENTS)
    with pytest.raises(ValidationError, match="too many attachments"):
        email(attachments=[att] * (main.MAX_ATTACHMENTS + 1))


def test_total_attachment_size_is_capped(monkeypatch):
    monkeypatch.setattr(main, "MAX_TOTAL_ATTACHMENT_BYTES", 1000)
    att = {"filename": "a.bin", "content": base64.b64encode(b"x" * 400).decode()}
    email(attachments=[att, att])
    with pytest.raises(ValidationError, match="in total"):
        email(attachments=[att, att, att])


@pytest.mark.parametrize("raw", [b"", b"a", b"ab", b"abc", b"abcd", b"x" * 1000])
def test_decoded_size_matches_real_decoding(raw):
    assert main._decoded_size(base64.b64encode(raw).decode()) == len(raw)


# ── per-wallet and global budgets ───────────────────────────────────────

def test_send_without_a_readable_payer_is_refused(fresh_counters):
    """Previously this skipped every limit and sent anyway."""
    with pytest.raises(HTTPException) as exc:
        main.send_email(request_from(wallet=None), email())
    assert exc.value.status_code == 500
    assert fresh_counters == []


def test_wallet_recipient_budget(fresh_counters, monkeypatch):
    monkeypatch.setattr(main, "DAILY_RECIPIENT_LIMIT_PER_WALLET", 6)
    monkeypatch.setattr(main, "DAILY_DOMAIN_LIMIT", 100)
    def three(i):
        return email(to=f"a{i}@x.example", cc=[f"b{i}@y.example"], bcc=[f"c{i}@z.example"])
    main.send_email(request_from(), three(1))
    main.send_email(request_from(), three(2))
    with pytest.raises(HTTPException) as exc:
        main.send_email(request_from(), three(3))
    assert exc.value.status_code == 429
    assert exc.value.detail["error"] == "wallet_recipient_limit_exceeded"
    assert len(fresh_counters) == 2
    # Case of the wallet address does not give a second budget.
    with pytest.raises(HTTPException):
        main.send_email(request_from(WALLET.upper().replace("0X", "0x")), three(4))


def test_global_budget_survives_wallet_rotation(fresh_counters, monkeypatch):
    """A fresh wallet per message used to reset every limit."""
    monkeypatch.setattr(main, "GLOBAL_DAILY_RECIPIENT_LIMIT", 5)
    for i in range(5):
        main.send_email(request_from(f"0x{i:040x}"), email(to=f"u{i}@d{i}.example"))
    with pytest.raises(HTTPException) as exc:
        main.send_email(request_from(f"0x{99:040x}"), email(to="late@late.example"))
    assert exc.value.status_code == 429
    assert exc.value.detail["error"] == "service_daily_limit_reached"
    assert len(fresh_counters) == 5


def test_refused_reservation_takes_nothing(monkeypatch):
    monkeypatch.setattr(main, "GLOBAL_DAILY_RECIPIENT_LIMIT", 4)
    main.reserve_recipients("0xa", 3)
    with pytest.raises(HTTPException):
        main.reserve_recipients("0xb", 2)
    main.reserve_recipients("0xb", 1)      # the remaining one is still there
    with pytest.raises(HTTPException):
        main.reserve_recipients("0xc", 1)


def test_existing_message_and_domain_limits_still_apply(fresh_counters, monkeypatch):
    monkeypatch.setattr(main, "DAILY_RECIPIENT_LIMIT_PER_WALLET", 1000)
    for i in range(main.DAILY_DOMAIN_LIMIT):
        main.send_email(request_from(), email(to=f"u{i}@same.example"))
    with pytest.raises(HTTPException) as exc:
        main.send_email(request_from(), email(to="again@same.example"))
    assert exc.value.detail["error"] == "domain_limit_exceeded"


# ── request size ────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return TestClient(main.app)


def test_oversized_request_is_refused_before_payment(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_REQUEST_BYTES", 2000)
    big = {"to": "a@one.example", "subject": "s", "body": "x" * 5000}
    assert client.post("/send", json=big).status_code == 413


def test_request_without_length_is_refused(client):
    def body():
        yield b'{"to": "a@one.example"}'
    assert client.post("/send", content=body(), headers={"Content-Type": "application/json"}).status_code == 411


def test_normal_unpaid_request_still_gets_a_payment_challenge(client):
    r = client.post("/send", json={"to": "a@one.example", "subject": "s", "body": "b"})
    assert r.status_code == 402


def test_other_routes_are_unaffected(client):
    assert client.get("/health").status_code == 200
    assert client.get("/send/test").status_code == 200
