import json
import logging
from types import SimpleNamespace
from urllib.error import URLError

import pytest

import mooring_data_generator.http_worker as http_worker


class FakePort:
    def __init__(self, payload):
        # Mimic pydantic model with model_dump(by_alias=True)
        self.data = SimpleNamespace(model_dump=lambda by_alias=True: payload)
        self.update_calls = 0

    def update(self):
        self.update_calls += 1


@pytest.fixture
def fake_port():
    return FakePort(payload={"hello": "world", "n": 1})


def _raise_keyboardinterrupt(*args, **kwargs):  # noqa: ANN001, ANN003
    raise KeyboardInterrupt


def test_run_posts_payload_and_updates_once(monkeypatch, fake_port):
    # Arrange: replace builder, urlopen and time.sleep
    calls = {}

    def fake_request(url, data=None, headers=None, method=None):  # noqa: ANN001, ANN201
        # Validate request building inputs
        calls["url"] = url
        calls["headers"] = headers
        calls["method"] = method
        calls["data"] = data
        return SimpleNamespace(url=url, data=data, headers=headers, method=method)

    class FakeResponse:
        def __enter__(self):  # noqa: D401
            # Return an object with read()
            return SimpleNamespace(read=lambda: b"ok")

        def __exit__(self, exc_type, exc, tb):  # noqa: D401, ANN001, ANN201
            return False

    monkeypatch.setattr(http_worker, "build_random_port", lambda: fake_port)
    monkeypatch.setattr(http_worker.urllib.request, "Request", fake_request)
    monkeypatch.setattr(
        http_worker.urllib.request, "urlopen", lambda req, timeout=10: FakeResponse()
    )
    monkeypatch.setattr(http_worker.time, "sleep", _raise_keyboardinterrupt)

    # Act: run until our sleep triggers KeyboardInterrupt (caught inside run)
    http_worker.run("http://example.test/ingest")

    # Assert
    assert calls["url"] == "http://example.test/ingest"
    assert calls["method"] == "POST"
    assert calls["headers"] == {"Content-Type": "application/json"}

    # Data should be JSON bytes of our payload
    sent_json = json.loads(calls["data"].decode("utf-8"))
    assert sent_json == {"hello": "world", "n": 1}

    # update should have been called exactly once (before the KeyboardInterrupt during sleep)
    assert fake_port.update_calls == 1


def test_run_logs_on_http_error_and_still_updates(monkeypatch, caplog, fake_port):
    # Arrange
    def fake_urlopen(req, timeout=10):  # noqa: ANN001, ANN201
        raise URLError("boom")

    monkeypatch.setattr(http_worker, "build_random_port", lambda: fake_port)
    monkeypatch.setattr(http_worker.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(http_worker.time, "sleep", _raise_keyboardinterrupt)

    caplog.set_level(logging.ERROR, logger=http_worker.__name__)

    # Act
    http_worker.run("http://example.test/ingest")

    # Assert: error was logged and update still called once
    assert any("HTTP send failed" in rec.message for rec in caplog.records)
    assert fake_port.update_calls == 1


def test_run_logs_info_on_keyboard_interrupt(monkeypatch, caplog, fake_port):
    # Make sleep raise KeyboardInterrupt so outer handler logs INFO
    monkeypatch.setattr(http_worker, "build_random_port", lambda: fake_port)
    monkeypatch.setattr(http_worker.time, "sleep", _raise_keyboardinterrupt)

    caplog.set_level(logging.INFO, logger=http_worker.__name__)

    # Act
    http_worker.run("http://example.test/ingest")

    # Assert: graceful shutdown was logged
    assert any(
        "Interrupted by user" in rec.message and rec.levelno == logging.INFO
        for rec in caplog.records
    )
