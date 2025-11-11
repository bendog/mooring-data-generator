import threading
from urllib import request

import pytest

from mooring_data_generator.receiver import (
    PrintingRequestHandler,
    ThreadingHTTPServer,
)


@pytest.fixture()
def http_server():
    # Start a test server bound to an ephemeral port on localhost
    server = ThreadingHTTPServer(("127.0.0.1", 0), PrintingRequestHandler)
    host, port = server.server_address

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://{host}:{port}", server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _http(method: str, url: str, data: bytes | None = None, headers: dict | None = None):
    req = request.Request(url, data=data, headers=headers or {}, method=method)
    with request.urlopen(req, timeout=5) as resp:  # noqa: S310 - local test server
        return resp.getcode(), resp.headers, resp.read()


def test_get_no_body_ok_and_prints(http_server, capsys):
    base_url, _ = http_server

    status, headers, body = _http("GET", f"{base_url}/")

    assert status == 200
    assert headers.get_content_type() == "text/plain"
    assert body == b"OK\n"

    out = capsys.readouterr().out
    # Contains client line, request line, headers section, and no body marker
    assert "Client: " in out
    assert "Request: GET / " in out  # method and path present
    assert "-- Headers --" in out
    assert "-- No Body --" in out


def test_post_truncates_body_when_max_show_small(http_server, capsys):
    base_url, _ = http_server

    # Temporarily reduce max_show
    orig = PrintingRequestHandler.max_show
    try:
        PrintingRequestHandler.max_show = 5
        payload = b"abcdefghij"  # 10 bytes
        status, headers, body = _http(
            "POST",
            f"{base_url}/echo",
            data=payload,
            headers={"Content-Type": "text/plain"},
        )
        assert status == 200
        assert body == b"OK\n"

        out = capsys.readouterr().out
        # Body section present and truncated print shown
        assert "-- Body (bytes) --" in out
        assert "abcde" in out  # first 5 bytes
        assert "-- 5 more bytes not shown --" in out
    finally:
        PrintingRequestHandler.max_show = orig


def test_post_prints_full_body_when_unlimited(http_server, capsys):
    base_url, _ = http_server

    orig = PrintingRequestHandler.max_show
    try:
        PrintingRequestHandler.max_show = None  # no truncation
        payload = b"abcdefghij"  # 10 bytes
        _ = _http(
            "POST",
            f"{base_url}/full",
            data=payload,
            headers={"Content-Type": "text/plain"},
        )

        out = capsys.readouterr().out
        assert "-- Body (bytes) --" in out
        assert "abcdefghij" in out
        # No truncation marker when unlimited
        assert "more bytes not shown" not in out
    finally:
        PrintingRequestHandler.max_show = orig


def test_options_returns_cors_headers(http_server):
    base_url, _ = http_server

    status, headers, body = _http("OPTIONS", f"{base_url}/anything")

    assert status == 200
    # CORS headers present
    assert headers.get("Access-Control-Allow-Origin") == "*"
    assert headers.get("Access-Control-Allow-Methods") == "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    assert headers.get("Access-Control-Allow-Headers") == "*, Content-Type, Authorization"
    # No body required
    assert body in (b"", None)


def test_post_with_format_mode_uses_json_dumps(http_server, capsys):
    base_url, _ = http_server

    orig_format = PrintingRequestHandler.format_mode
    try:
        PrintingRequestHandler.format_mode = True
        payload = b'{"test": "content", "value": 123}'
        status, headers, body = _http(
            "POST",
            f"{base_url}/test",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        assert status == 200
        assert body == b"OK\n"

        out = capsys.readouterr().out
        # Should still have standard headers
        assert "Client: " in out
        assert "Request: POST /test " in out
        assert "-- Headers --" in out
        assert "-- Body (bytes) --" in out
        # Body should be JSON-formatted with indentation (json.dumps with indent=2)
        assert '"test": "content"' in out
        assert '"value": 123' in out
    finally:
        PrintingRequestHandler.format_mode = orig_format


def test_post_without_format_mode_plain_output(http_server, capsys):
    base_url, _ = http_server

    orig_format = PrintingRequestHandler.format_mode
    try:
        PrintingRequestHandler.format_mode = False
        payload = b"test content"
        status, headers, body = _http(
            "POST",
            f"{base_url}/test",
            data=payload,
            headers={"Content-Type": "text/plain"},
        )
        assert status == 200
        assert body == b"OK\n"

        out = capsys.readouterr().out
        # Should have standard output format
        assert "Client: " in out
        assert "Request: POST /test " in out
        assert "-- Headers --" in out
        assert "-- Body (bytes) --" in out
        # Body should be plain text (not JSON-formatted)
        assert "test content" in out
        # Should NOT have JSON quotes around it
        assert out.count('"test content"') == 0
    finally:
        PrintingRequestHandler.format_mode = orig_format
