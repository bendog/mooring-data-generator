import json
import logging
from types import SimpleNamespace

import pytest

import mooring_data_generator.builder as builder
from mooring_data_generator.models import HookData, ShipData


def test_random_single_use_choice_removes_item(monkeypatch):
    calls = {"choices": []}

    def choose_first(seq):  # noqa: ANN001
        calls["choices"].append(list(seq))
        return seq[0]

    monkeypatch.setattr(builder.random, "choice", choose_first)

    items = ["a", "b", "c"]
    picked = builder.random_single_use_choice(items)

    assert picked == "a"
    # Should be removed from original list
    assert items == ["b", "c"]


def test_random_name_helpers_use_globals_and_are_unique(monkeypatch):
    # Provide tiny deterministic pools
    monkeypatch.setattr(builder, "NAUTICAL_SUPERLATIVES", ["Valiant", "Noble"])  # type: ignore[attr-defined]
    monkeypatch.setattr(builder, "NAUTICAL_BASE_NAMES", ["Amelia", "Sophia"])  # type: ignore[attr-defined]
    monkeypatch.setattr(builder, "WA_PORT_NAMES", ["Fremantle", "Kwinana"])  # type: ignore[attr-defined]
    monkeypatch.setattr(builder, "BOLLARD_NAMES", ["BOL001", "BOL002"])  # type: ignore[attr-defined]

    # Always pick the first available
    monkeypatch.setattr(builder.random, "choice", lambda seq: seq[0])

    # Ship name consumes one from each list
    name1 = builder.random_ship_name()
    assert name1 == "Valiant Amelia"
    # Second call uses remaining items
    name2 = builder.random_ship_name()
    assert name2 == "Noble Sophia"

    # WA port unique selection
    port1 = builder.random_wa_port_name()
    port2 = builder.random_wa_port_name()
    assert {port1, port2} == {"Fremantle", "Kwinana"}

    # Bollard name unique selection
    bollard1 = builder.random_bollard_name()
    bollard2 = builder.random_bollard_name()
    assert {bollard1, bollard2} == {"BOL001", "BOL002"}


def test_generate_ship_uses_ship_ids_and_name(monkeypatch):
    # Fix ship ids
    monkeypatch.setattr(builder, "SHIP_IDS", ["0001", "0002"])  # type: ignore[attr-defined]
    # Fix ship name to avoid mutating name pools in this test
    monkeypatch.setattr(builder, "random_ship_name", lambda: "Majestic Test")
    # Always pick first
    monkeypatch.setattr(builder.random, "choice", lambda seq: seq[0])

    ship = builder.generate_ship()
    assert isinstance(ship, ShipData)
    assert ship.name == "Majestic Test"
    assert ship.vessel_id == "0001"
    # Ensure id pool was consumed
    assert builder.SHIP_IDS == ["0002"]


def test_hookworker_active_and_update(monkeypatch):
    # Active and non-faulted (hook_status=True)
    # Make gauss determinate for tension: ceil(abs(3.2)) -> 4
    monkeypatch.setattr(builder.random, "gauss", lambda mu, sigma: 3.2)  # noqa: ARG005

    hw = builder.HookWorker(hook_number=7, hook_status=True, attached_line="HEAD")
    # On init, because active=True, update() called -> tension set
    assert hw.name == "Hook 7"
    assert hw.attached_line == "HEAD"
    assert hw.tension == 4
    assert hw.fault is False

    # Update again should keep producing valid integer tension
    hw.update()
    assert isinstance(hw.tension, int)
    assert hw.tension >= 0

    data = hw.data
    assert isinstance(data, HookData)
    dumped = data.model_dump()
    assert dumped["name"] == "Hook 7"
    assert dumped["attached_line"] == "HEAD"


def test_hookworker_inactive_has_no_tension(monkeypatch):
    # Inactive (hook_status=False)
    hw = builder.HookWorker(hook_number=1, hook_status=False, attached_line="BREAST")
    assert hw.attached_line is None
    assert hw.tension is None


@pytest.mark.parametrize(
    "bollard_number,total_bollards,expected_line",
    [
        (1, 10, "HEAD"),  # 0.1
        (3, 10, "SPRING"),  # 0.3
        (5, 10, "BREAST"),  # 0.5
        (9, 10, "STERN"),  # 0.9
    ],
)
def test_bollardworker_hook_attachment_and_numbering(
    monkeypatch, bollard_number, total_bollards, expected_line
):
    # Hooks active and non-faulted; deterministic tension
    monkeypatch.setattr(builder.random, "gauss", lambda mu, sigma: 1.1)  # tension -> ceil(1.1)=2
    # Deterministic bollard names
    monkeypatch.setattr(builder, "random_bollard_name", lambda: f"BOL{bollard_number:03d}")

    # Determine attached line for this bollard
    attached_line = builder.line_name_generator(list(range(1, total_bollards + 1)))[
        bollard_number - 1
    ]
    # Provide hook statuses: 3 active, non-faulted
    hook_statuses = (True, True, True)

    bw = builder.BollardWorker(
        bollard_number=bollard_number, attached_line=attached_line, hook_statuses=hook_statuses
    )

    # 3 hooks per bollard
    assert len(bw.hooks) == builder.HOOK_COUNT_MULTIPLIER
    # Verify numbering
    start = (bollard_number * builder.HOOK_COUNT_MULTIPLIER) - builder.HOOK_COUNT_MULTIPLIER + 1
    names = [h.name for h in bw.hooks]
    assert names == [f"Hook {n}" for n in range(start, start + builder.HOOK_COUNT_MULTIPLIER)]

    # All hooks should have expected attached line when active
    for h in bw.hooks:
        assert h.attached_line == expected_line
        assert h.tension == 2  # from gauss 1.1 -> ceil -> 2


def test_radarworker_init_update_and_data(monkeypatch):
    # Provide a generator of values for gauss calls
    values = iter([12.5, 0.7, 8.0])  # init distance, init change, update new_distance
    monkeypatch.setattr(builder.random, "gauss", lambda mu, sigma: next(values))  # noqa: ARG005

    rw = builder.RadarWorker("BARD1", active=True)
    assert rw.active is True
    assert rw.distance == pytest.approx(12.5)
    assert rw.change == pytest.approx(0.7)

    # Update computes new distance and absolute change
    d, c = rw.update()
    assert d == pytest.approx(8.0)
    assert c == pytest.approx(abs(12.5 - 8.0))

    data = rw.data
    assert data.name == "BARD1"
    assert data.distance_status == "ACTIVE"
    assert data.ship_distance == pytest.approx(8.0)


def test_berthworker_composition_and_naming(monkeypatch):
    # Make deterministic: 10 bollards -> 30 hooks; 5 radars named B<code>RD1..5
    # Set bollard_count via gauss -> ceil(10.0) = 10
    def gauss_stub(mu, sigma):  # noqa: ANN001, ARG001
        return 10.0

    monkeypatch.setattr(builder.random, "gauss", gauss_stub)

    # Radar count selection to 5 for range(1, choice+1)
    monkeypatch.setattr(builder.random, "choice", lambda seq: 5 if seq == [5, 6, 6, 6] else seq[0])

    # Make all radars inactive and hooks inactive/non-faulted for determinism
    def choices_stub(seq, weights=None, k=None):  # noqa: ANN001, ARG001
        if seq == [True, False] and k is not None:
            return [False] * k
        if tuple(seq) == (True, False, None) and k is not None:
            return [False] * k
        return [seq[0]] * (k if k is not None else 1)

    monkeypatch.setattr(builder.random, "choices", choices_stub)
    # Deterministic children
    monkeypatch.setattr(builder, "random_bollard_name", lambda: "BOL999")
    monkeypatch.setattr(
        builder, "generate_ship", lambda: ShipData(name="Test Ship", vessel_id="1234")
    )

    bw = builder.BerthWorker("A")

    assert bw.name == "Berth A"
    assert bw.bollard_count == 10
    assert bw.hook_count == 30
    assert len(bw.radars) == 5
    assert [r.name for r in bw.radars] == ["BARD1", "BARD2", "BARD3", "BARD4", "BARD5"]
    assert len(bw.bollards) == 10

    # Data is a Pydantic model with nested models
    data = bw.data
    dumped = data.model_dump()
    assert dumped["name"] == "Berth A"
    assert dumped["bollard_count"] == 10
    assert dumped["hook_count"] == 30
    assert dumped["ship"]["vessel_id"] == "1234"
    assert len(dumped["radars"]) == 5
    assert len(dumped["bollards"]) == 10


def test_portworker_builds_expected_structure(monkeypatch):
    # Fix randoms
    monkeypatch.setattr(builder, "random_wa_port_name", lambda: "Fremantle")
    monkeypatch.setattr(builder.random, "randint", lambda a, b: 2)  # 2 berths
    # Deterministic children
    monkeypatch.setattr(
        builder, "generate_ship", lambda: ShipData(name="SS Test", vessel_id="9876")
    )
    monkeypatch.setattr(builder, "random_bollard_name", lambda: "BOL111")
    # For radar count per berth and inactive radars/hooks
    monkeypatch.setattr(builder.random, "choice", lambda seq: 5 if seq == [5, 6, 6, 6] else seq[0])

    def choices_stub(seq, weights=None, k=None):  # noqa: ANN001, ARG001
        if seq == [True, False] and k is not None:
            return [False] * k
        if tuple(seq) == (True, False, None) and k is not None:
            return [False] * k
        return [seq[0]] * (k if k is not None else 1)

    monkeypatch.setattr(builder.random, "choices", choices_stub)

    port = builder.PortWorker()
    assert port.name == "Fremantle"
    assert len(port.berths) == 2

    # NB: Current implementation uses "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[berth_num], so first is "B"
    assert port.berths[0].name == "Berth B"
    assert port.berths[1].name == "Berth C"

    pdata = port.data
    dumped = pdata.model_dump()
    assert dumped["name"] == "Fremantle"
    assert len(dumped["berths"]) == 2


def test_build_random_port_returns_portworker():
    port = builder.build_random_port()
    assert isinstance(port, builder.PortWorker)


def test_main_logs_json_payload(monkeypatch, caplog):
    # Replace build_random_port with fake object exposing .data.model_dump
    payload = {"hello": "world"}
    fake_port = SimpleNamespace(data=SimpleNamespace(model_dump=lambda by_alias=True: payload))

    monkeypatch.setattr(builder, "build_random_port", lambda: fake_port)

    caplog.set_level(logging.INFO, logger=builder.__name__)

    builder.main()

    # Should have logged a JSON string of the payload at INFO level
    messages = [rec.message for rec in caplog.records if rec.levelno == logging.INFO]
    assert any(json.dumps(payload, ensure_ascii=False, indent=2) in msg for msg in messages)
