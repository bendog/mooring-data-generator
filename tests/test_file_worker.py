import json
import logging
from datetime import datetime
from types import SimpleNamespace

import pytest

import mooring_data_generator.file_worker as file_worker


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


def test_run_writes_file_with_correct_format_and_updates_once(monkeypatch, fake_port, tmp_path):
    # Arrange: replace builder, datetime, and time.sleep
    calls = {}
    test_path = tmp_path / "output.json"
    fixed_datetime = datetime(2025, 11, 11, 7, 49, 30)
    original_open = open

    class FakeDatetime:
        @staticmethod
        def now():  # noqa: ANN201
            return fixed_datetime

        @staticmethod
        def strftime(fmt):  # noqa: ANN001, ANN201
            return fixed_datetime.strftime(fmt)

    def fake_open(file, mode="r", **kwargs):  # noqa: ANN001, ANN201
        calls["output_file"] = file
        calls["mode"] = mode
        # Use original open for actual file writing
        return original_open(file, mode, **kwargs)

    monkeypatch.setattr(file_worker, "build_random_port", lambda: fake_port)
    monkeypatch.setattr(file_worker, "datetime", FakeDatetime)
    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(file_worker.time, "sleep", _raise_keyboardinterrupt)

    # Act: run until our sleep triggers KeyboardInterrupt (caught inside run)
    file_worker.run(test_path)

    # Assert: file was written with correct naming pattern
    expected_filename = tmp_path / "output_20251111074930.json"
    assert calls["output_file"] == expected_filename
    assert calls["mode"] == "w"

    # Verify file exists and contains correct JSON
    assert expected_filename.exists()
    with open(expected_filename, "r", encoding="utf-8") as f:
        written_data = json.load(f)
    assert written_data == {"hello": "world", "n": 1}

    # update should have been called exactly once (before the KeyboardInterrupt during sleep)
    assert fake_port.update_calls == 1


def test_run_creates_parent_directory_if_missing(monkeypatch, fake_port, tmp_path):
    # Arrange: test with nested path that doesn't exist
    nested_path = tmp_path / "nested" / "dir" / "output.json"
    fixed_datetime = datetime(2025, 11, 11, 8, 0, 0)

    class FakeDatetime:
        @staticmethod
        def now():  # noqa: ANN201
            return fixed_datetime

    monkeypatch.setattr(file_worker, "build_random_port", lambda: fake_port)
    monkeypatch.setattr(file_worker, "datetime", FakeDatetime)
    monkeypatch.setattr(file_worker.time, "sleep", _raise_keyboardinterrupt)

    # Act
    file_worker.run(nested_path)

    # Assert: parent directories were created
    expected_file = tmp_path / "nested" / "dir" / "output_20251111080000.json"
    assert expected_file.exists()
    with open(expected_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {"hello": "world", "n": 1}


def test_run_logs_on_file_error_and_still_updates(monkeypatch, caplog, fake_port, tmp_path):
    # Arrange: make file writing fail
    test_path = tmp_path / "output.json"

    def fake_open(file, mode="r", **kwargs):  # noqa: ANN001, ANN201
        raise OSError("disk full")

    monkeypatch.setattr(file_worker, "build_random_port", lambda: fake_port)
    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(file_worker.time, "sleep", _raise_keyboardinterrupt)

    caplog.set_level(logging.ERROR, logger=file_worker.__name__)

    # Act
    file_worker.run(test_path)

    # Assert: error was logged and update still called once
    assert any("File write failed" in rec.message for rec in caplog.records)
    assert fake_port.update_calls == 1


def test_run_logs_on_ioerror_and_still_updates(monkeypatch, caplog, fake_port, tmp_path):
    # Arrange: make file writing fail with IOError
    test_path = tmp_path / "output.json"

    def fake_open(file, mode="r", **kwargs):  # noqa: ANN001, ANN201
        raise IOError("permission denied")

    monkeypatch.setattr(file_worker, "build_random_port", lambda: fake_port)
    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr(file_worker.time, "sleep", _raise_keyboardinterrupt)

    caplog.set_level(logging.ERROR, logger=file_worker.__name__)

    # Act
    file_worker.run(test_path)

    # Assert: error was logged and update still called once
    assert any("File write failed" in rec.message for rec in caplog.records)
    assert fake_port.update_calls == 1


def test_run_logs_info_on_keyboard_interrupt(monkeypatch, caplog, fake_port, tmp_path):
    # Make sleep raise KeyboardInterrupt so outer handler logs INFO
    test_path = tmp_path / "output.json"

    monkeypatch.setattr(file_worker, "build_random_port", lambda: fake_port)
    monkeypatch.setattr(file_worker.time, "sleep", _raise_keyboardinterrupt)

    caplog.set_level(logging.INFO, logger=file_worker.__name__)

    # Act
    file_worker.run(test_path)

    # Assert: graceful shutdown was logged
    assert any(
        "Interrupted by user" in rec.message and rec.levelno == logging.INFO
        for rec in caplog.records
    )


def test_run_handles_update_exception(monkeypatch, fake_port, tmp_path):
    # Arrange: make port.update() raise an exception
    test_path = tmp_path / "output.json"

    def fake_update():  # noqa: ANN201
        raise RuntimeError("update failed")

    fake_port.update = fake_update

    monkeypatch.setattr(file_worker, "build_random_port", lambda: fake_port)

    # Act & Assert: update exception should be raised
    with pytest.raises(RuntimeError, match="update failed"):
        file_worker.run(test_path)


def test_run_multiple_iterations_with_different_timestamps(monkeypatch, fake_port, tmp_path):
    # Arrange: mock datetime to return different timestamps
    timestamps = [
        datetime(2025, 11, 11, 8, 0, 0),
        datetime(2025, 11, 11, 8, 0, 2),
    ]
    timestamp_iter = iter(timestamps)

    class FakeDatetime:
        @staticmethod
        def now():  # noqa: ANN201
            return next(timestamp_iter)

    call_count = [0]

    def fake_sleep(seconds):  # noqa: ANN001, ANN201
        call_count[0] += 1
        if call_count[0] >= 2:
            raise KeyboardInterrupt

    test_path = tmp_path / "data.json"

    monkeypatch.setattr(file_worker, "build_random_port", lambda: fake_port)
    monkeypatch.setattr(file_worker, "datetime", FakeDatetime)
    monkeypatch.setattr(file_worker.time, "sleep", fake_sleep)

    # Act
    file_worker.run(test_path)

    # Assert: two files should have been created with different timestamps
    file1 = tmp_path / "data_20251111080000.json"
    file2 = tmp_path / "data_20251111080002.json"

    assert file1.exists()
    assert file2.exists()

    # Both should contain the same payload
    with open(file1, "r", encoding="utf-8") as f:
        data1 = json.load(f)
    with open(file2, "r", encoding="utf-8") as f:
        data2 = json.load(f)

    assert data1 == {"hello": "world", "n": 1}
    assert data2 == {"hello": "world", "n": 1}

    # update should have been called twice
    assert fake_port.update_calls == 2
