"""
Security review 2026-11-18: guarded fetching in the conversion service.

Server PUBLIC plays a normal website; server INTERNAL plays an address the
service must never read from. Both live on 127.0.0.1, so the two address
checks are patched to tell them apart by port.

Run (from x402-conversion-api/):
      pip install -r requirements.txt pytest
      pytest tests/
"""

import asyncio
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import httpx
import pytest

os.environ.setdefault("PAY_TO_ADDRESS", "0x0000000000000000000000000000000000000001")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main  # noqa: E402


class Site(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.hits.append(self.path)
        internal = f"http://127.0.0.1:{self.server.other_port}"
        redirects = {
            "/to-internal": internal + "/secret.csv",
            "/to-public": "/data.csv",            # relative Location
            "/loop": "/loop",
            "/hop1": "/hop2", "/hop2": "/to-internal",
        }
        if self.path in redirects:
            self.send_response(302)
            self.send_header("Location", redirects[self.path])
            self.end_headers()
            return
        if self.path == "/big":
            body = b"x" * (main.MAX_FILE_BYTES + 1024)
        elif self.path == "/page.html":
            body = (f'<html><body><p>hello</p><img src="http://127.0.0.1:{self.server.server_port}/to-internal">'
                    f'<link rel="stylesheet" href="{internal}/secret.css"></body></html>').encode()
        else:
            body = b"name,value\nSECRET,internal\n" if self.server.is_internal else b"name,value\nok,public\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def net(monkeypatch):
    public = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    internal = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    for srv, other, is_internal in ((public, internal, False), (internal, public, True)):
        srv.hits = []
        srv.other_port = other.server_port
        srv.is_internal = is_internal
        threading.Thread(target=srv.serve_forever, daemon=True).start()

    def fake_validate(url):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("scheme not allowed")
        if parsed.port == internal.server_port:
            raise ValueError("URL resolves to blocked IP range: internal")

    monkeypatch.setattr(main, "validate_url_for_ssrf", fake_validate)
    monkeypatch.setattr(main, "_peer_is_public", lambda peer: not peer or peer[1] != internal.server_port)

    class Net:
        base = f"http://127.0.0.1:{public.server_port}"
        internal_base = f"http://127.0.0.1:{internal.server_port}"
        public_hits = public.hits
        internal_hits = internal.hits
        internal_port = internal.server_port

    yield Net
    public.shutdown(); internal.shutdown()
    public.server_close(); internal.server_close()


def download(url):
    return asyncio.run(main.download_file(url))


def test_public_download_works(net):
    assert download(net.base + "/data.csv") == b"name,value\nok,public\n"


def test_direct_internal_is_refused_and_never_requested(net):
    with pytest.raises(ValueError):
        download(net.internal_base + "/secret.csv")
    assert net.internal_hits == []


@pytest.mark.parametrize("path", ["/to-internal", "/hop1"])
def test_redirect_to_internal_is_refused_and_never_requested(net, path):
    with pytest.raises(ValueError):
        download(net.base + path)
    assert net.internal_hits == []


def test_relative_redirect_between_public_pages_works(net):
    """The old hook validated the raw Location header and so rejected
    relative redirects outright."""
    assert download(net.base + "/to-public") == b"name,value\nok,public\n"


def test_redirect_loop_is_cut_off(net):
    with pytest.raises(ValueError, match="Too many redirects"):
        download(net.base + "/loop")
    assert len(net.public_hits) == main.MAX_REDIRECTS + 1


def test_oversize_download_is_stopped(net):
    with pytest.raises(ValueError, match="10MB"):
        download(net.base + "/big")


def test_peer_address_is_what_counts(net, monkeypatch):
    """DNS that changes after the check: the URL check passes, the socket
    lands on the internal server, and the body is never read."""
    monkeypatch.setattr(main, "validate_url_for_ssrf", lambda url: None)
    with pytest.raises(ValueError, match="blocked IP range"):
        download(net.internal_base + "/secret.csv")


def test_real_peer_address_is_available(monkeypatch):
    """Guards the guard: httpx must expose the peer address, or
    _assert_response_peer_public would silently pass everything."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    srv.hits, srv.other_port, srv.is_internal = [], 1, False
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with httpx.Client(trust_env=False) as client:
            with client.stream("GET", f"http://127.0.0.1:{srv.server_port}/data.csv") as response:
                peer = response.extensions["network_stream"].get_extra_info("server_addr")
                assert peer[0] == "127.0.0.1" and peer[1] == srv.server_port
                assert main._peer_is_public(peer) is False   # loopback, unpatched
    finally:
        srv.shutdown(); srv.server_close()


@pytest.mark.parametrize("url", [
    "http://169.254.169.254\\@example.com/latest/meta-data/",
    "http://example.com/ a",
    "http://example.com/\tx",
    "http://exam\nple.com/",
])
def test_ambiguous_urls_are_rejected(url):
    with pytest.raises(ValueError):
        main._check_fetch_url(url)


def test_the_normalised_backslash_url_is_also_blocked():
    """What pydantic turns the backslash URL into is itself an internal
    address, and the check that now runs on the fetched string sees that."""
    from pydantic_core import Url
    normalised = str(Url("http://169.254.169.254\\@example.com/latest/meta-data/"))
    assert urlparse(normalised).hostname == "169.254.169.254"
    with pytest.raises(ValueError):
        main._check_fetch_url(normalised)


# ── WeasyPrint secondary fetches ────────────────────────────────────────

def test_fetcher_follows_only_checked_hops(net):
    with pytest.raises(ValueError):
        main.safe_url_fetcher(net.base + "/to-internal")
    assert net.internal_hits == []
    result = main.safe_url_fetcher(net.base + "/to-public")
    assert result.read() == b"name,value\nok,public\n"
    assert result.content_type == "text/csv"
    assert result.charset == "utf-8"
    assert result.url == net.base + "/data.csv"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "gopher://example.com/"])
def test_fetcher_refuses_other_schemes(url):
    with pytest.raises(ValueError):
        main.safe_url_fetcher(url)


def test_fetcher_allows_inline_data_uris():
    result = main.safe_url_fetcher("data:text/css;base64,Ym9keXt9")
    assert result.read() == b"body{}"


def test_html_to_pdf_never_reads_internal_resources(net):
    html = download(net.base + "/page.html")
    pdf = main.sync_html_to_pdf(html, net.base + "/page.html")
    assert pdf.startswith(b"%PDF")
    assert net.internal_hits == []


def test_html_to_pdf_still_loads_public_resources(net):
    html = f'<html><head><link rel="stylesheet" href="{net.base}/style.css"></head><body>hi</body></html>'.encode()
    pdf = main.sync_html_to_pdf(html, net.base + "/doc.html")
    assert pdf.startswith(b"%PDF")
    assert "/style.css" in net.public_hits
