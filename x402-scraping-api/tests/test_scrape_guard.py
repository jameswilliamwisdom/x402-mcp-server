"""
Security review 2026-11-18: the scrape guard.

Two local HTTP servers stand in for the internet. Server PUBLIC plays a
normal website; server INTERNAL plays an address the service must never
reach or reveal (in production: loopback, private ranges, cloud metadata).
Both really live on 127.0.0.1, so the two address checks are patched to
tell them apart by port.

Run (from x402-scraping-api/):
      pip install -r requirements.txt pytest
      playwright install chromium
      pytest tests/
"""

import asyncio
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import pytest
from fastapi import HTTPException
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main  # noqa: E402

ONE_PIXEL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360f8cfc0000003010100c9fe92ef0000000049454e44ae426082"
)


class Site(BaseHTTPRequestHandler):
    def _send(self, status, body=b"", ctype="text/html", headers=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _handle(self):
        self.server.hits.append((self.command, self.path))
        internal = f"http://127.0.0.1:{self.server.other_port}"
        here = f"http://127.0.0.1:{self.server.server_port}"
        routes = {
            "/ok": (200, b"<html><body><h1>public page</h1></body></html>"),
            "/to-internal": (302, b"", {"Location": internal + "/secret"}),
            "/to-internal-307": (307, b"", {"Location": internal + "/secret"}),
            "/to-internal-png": (302, b"", {"Location": internal + "/secret.png"}),
            "/to-public": (302, b"", {"Location": "/ok"}),
            "/loop": (302, b"", {"Location": "/loop"}),
            "/script-direct": (200, f'<html><body>x<script src="{internal}/secret.js"></script></body></html>'.encode()),
            "/fetch-redirect": (200, (
                "<html><body><div id=out>none</div><script>fetch('%s/to-internal')"
                ".then(r=>r.text()).then(t=>{document.getElementById('out').textContent=t})"
                ".catch(()=>{})</script></body></html>" % here).encode()),
            "/frame-redirect": (200, f'<html><body>x<iframe src="{here}/to-internal"></iframe></body></html>'.encode()),
            "/post-redirect": (200, (
                "<html><body>x<script>fetch('%s/to-internal-307',{method:'POST',body:'a=1'})"
                ".catch(()=>{})</script></body></html>" % here).encode()),
            "/meta-refresh": (200, f'<html><head><meta http-equiv="refresh" content="0;url={internal}/secret"></head><body>before</body></html>'.encode()),
        }
        if self.path in routes:
            status, body, *rest = routes[self.path]
            return self._send(status, body, headers=rest[0] if rest else None)
        if self.path.endswith(".png"):
            return self._send(200, ONE_PIXEL_PNG, ctype="image/png")
        self._send(200, b"<html><body>SECRET INTERNAL PAGE</body></html>")

    do_GET = do_POST = _handle

    def log_message(self, *args):
        pass


@pytest.fixture
def net(monkeypatch):
    public = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    internal = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    for srv, other in ((public, internal), (internal, public)):
        srv.hits = []
        srv.other_port = other.server_port
        threading.Thread(target=srv.serve_forever, daemon=True).start()

    def fake_validate(url):
        parsed = urlparse(url)
        if parsed.scheme not in main.ALLOWED_SCHEMES:
            raise ValueError("scheme not allowed")
        if parsed.port == internal.server_port:
            raise ValueError("URL resolves to blocked IP range: internal")

    monkeypatch.setattr(main, "validate_url_for_ssrf", fake_validate)
    monkeypatch.setattr(
        main, "_server_addr_is_public",
        lambda addr: not addr or addr.get("port") != internal.server_port,
    )

    class Net:
        base = f"http://127.0.0.1:{public.server_port}"
        internal_base = f"http://127.0.0.1:{internal.server_port}"
        public_hits = public.hits
        internal_hits = internal.hits

    yield Net
    public.shutdown(); internal.shutdown()
    public.server_close(); internal.server_close()


def scrape(url):
    async def go():
        async with async_playwright() as p:
            main.browser = await p.chromium.launch()
            try:
                return await main.scrape_page(url, None)
            finally:
                await main.browser.close()
                main.browser = None
    return asyncio.run(go())


def assert_blocked(url):
    with pytest.raises(HTTPException) as exc:
        scrape(url)
    assert exc.value.status_code == 400
    assert "SSRF" in exc.value.detail


def test_public_page_is_scraped(net):
    data = scrape(net.base + "/ok")
    assert "public page" in data["html"]
    assert data["status_code"] == 200
    assert data["final_url"] == net.base + "/ok"


def test_direct_internal_url_is_blocked_and_never_requested(net):
    assert_blocked(net.internal_base + "/secret")
    assert net.internal_hits == []


def test_redirect_to_internal_is_blocked_and_never_requested(net):
    """The confirmed finding: a public URL that 302s to an internal one used
    to come back with the internal page's HTML."""
    assert_blocked(net.base + "/to-internal")
    assert net.internal_hits == []


def test_redirect_between_public_pages_still_works(net):
    data = scrape(net.base + "/to-public")
    assert "public page" in data["html"]
    assert data["final_url"] == net.base + "/ok"


def test_redirect_loop_is_cut_off(net):
    assert_blocked(net.base + "/loop")
    assert len(net.public_hits) <= main.MAX_REDIRECTS + 2


def test_internal_subresource_is_not_requested(net):
    assert "SECRET" not in scrape(net.base + "/script-direct")["html"]
    assert net.internal_hits == []


def test_fetch_redirected_to_internal_returns_nothing(net):
    """Page script fetches a public URL that redirects to an internal one.
    The internal server here allows cross-origin reads (as the sibling
    services do), so without the guard its body lands in the page's HTML."""
    assert_blocked(net.base + "/fetch-redirect")


def test_frame_redirected_to_internal_is_never_requested(net):
    assert "SECRET" not in scrape(net.base + "/frame-redirect")["html"]
    assert net.internal_hits == []


def test_post_redirected_to_internal_is_never_sent(net):
    scrape(net.base + "/post-redirect")
    assert net.internal_hits == []


def test_images_are_still_skipped(net):
    """The old second route handler shadowed the resource-type block."""
    assert ("GET", "/secret.png") not in net.public_hits
    scrape(net.base + "/ok")


@pytest.mark.parametrize("addr, public", [
    (None, True), ({}, True),
    ({"ipAddress": "93.184.216.34", "port": 443}, True),
    ({"ipAddress": "127.0.0.1", "port": 80}, False),
    ({"ipAddress": "10.0.0.5", "port": 80}, False),
    ({"ipAddress": "169.254.169.254", "port": 80}, False),
    ({"ipAddress": "[::1]", "port": 80}, False),
    ({"ipAddress": "::ffff:10.0.0.1", "port": 80}, False),
])
def test_peer_address_classification(addr, public):
    assert main._server_addr_is_public(addr) is public
