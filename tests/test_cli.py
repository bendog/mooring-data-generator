import json
import sys
from types import SimpleNamespace

import pytest


def test_main_invokes_run_and_prints(monkeypatch, capsys, caplog):
    # Arrange: provide URL arg and capture run() invocation
    called = SimpleNamespace(url=None)

    def fake_run(url: str) -> None:
        called.url = url
        # Do not loop or block; just return
        return

    # Patch run in the http_worker module
    monkeypatch.setattr("mooring_data_generator.http_worker.run", fake_run, raising=True)

    # Patch argv for argparse within cli.main
    monkeypatch.setenv("PYTHONHASHSEED", "0")  # stability for any hashing if needed
    monkeypatch.setattr(sys, "argv", ["prog", "http://example.test/ingest"], raising=True)

    # Import after patches so module-level items resolve correctly
    import mooring_data_generator.cli as cli

    # Capture logs at INFO level
    caplog.set_level("INFO")

    # Act
    cli.main()

    # Assert: run was invoked with the exact URL
    assert called.url == "http://example.test/ingest"

    # Assert: user-facing prints
    out = capsys.readouterr().out
    assert (
        "Starting mooring data generator and will HTTP POST to http://example.test/ingest" in out
    )
    assert "Press CTRL+C to stop mooring data generator." in out

    # Assert: an info log was also emitted
    assert any(
        "Starting mooring data generator and will HTTP POST to http://example.test/ingest"
        in rec.getMessage()
        for rec in caplog.records
    )


def test_main_exits_when_no_url_provided(monkeypatch):
    # Arrange: no URL argument
    monkeypatch.setattr(sys, "argv", ["prog"], raising=True)

    import mooring_data_generator.cli as cli

    # Ensure we use the already imported module (parser is module-level), but argv is read by parse_args at runtime
    # Act & Assert: argparse should call SystemExit with code 2 when required positional arg is missing
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


def test_main_with_openapi_flag_outputs_valid_json(monkeypatch, capsys):
    # Arrange: provide --openapi flag
    monkeypatch.setattr(sys, "argv", ["prog", "--openapi"], raising=True)

    import mooring_data_generator.cli as cli

    # Act
    cli.main()

    # Assert: output is valid JSON
    out = capsys.readouterr().out
    parsed = json.loads(out)  # Should not raise exception
    assert parsed is not None
    assert isinstance(parsed, dict)


def test_main_with_openapi_flag_outputs_valid_openapi_spec(monkeypatch, capsys):
    # Arrange: provide --openapi flag
    monkeypatch.setattr(sys, "argv", ["prog", "--openapi"], raising=True)

    import mooring_data_generator.cli as cli

    # Act
    cli.main()

    # Assert: output contains OpenAPI specification structure
    out = capsys.readouterr().out
    spec = json.loads(out)

    # Check required OpenAPI fields
    assert "openapi" in spec
    assert spec["openapi"].startswith("3.0")
    assert "info" in spec
    assert "title" in spec["info"]
    assert "version" in spec["info"]
    assert "paths" in spec
    assert "components" in spec
    assert "schemas" in spec["components"]


def test_main_with_openapi_flag_does_not_require_url(monkeypatch, capsys):
    # Arrange: provide only --openapi flag, no url
    monkeypatch.setattr(sys, "argv", ["prog", "--openapi"], raising=True)

    import mooring_data_generator.cli as cli

    # Act: should not raise SystemExit
    cli.main()

    # Assert: successfully generated output
    out = capsys.readouterr().out
    spec = json.loads(out)
    assert "openapi" in spec


def test_main_with_openapi_flag_does_not_run_generator(monkeypatch, capsys):
    # Arrange: provide --openapi flag and mock run to ensure it's not called
    called = SimpleNamespace(http_called=False, file_called=False)

    def fake_http_run(url: str) -> None:
        called.http_called = True

    def fake_file_run(file_path) -> None:
        called.file_called = True

    monkeypatch.setattr("mooring_data_generator.http_worker.run", fake_http_run, raising=True)
    monkeypatch.setattr("mooring_data_generator.file_worker.run", fake_file_run, raising=True)
    monkeypatch.setattr(sys, "argv", ["prog", "--openapi"], raising=True)

    import mooring_data_generator.cli as cli

    # Act
    cli.main()

    # Assert: neither worker was called
    assert not called.http_called
    assert not called.file_called

    # Assert: OpenAPI spec was output
    out = capsys.readouterr().out
    spec = json.loads(out)
    assert "openapi" in spec
