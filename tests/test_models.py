import pytest
from pydantic import ValidationError

from mooring_data_generator.models import (
    TENSION_LIMITS,
    BerthData,
    BollardData,
    HookData,
    PortData,
    RadarData,
    ShipData,
)


def test_ship_data_serializes_with_camel_case_aliases():
    ship = ShipData(name="Evergreen", vessel_id="1234")

    dumped = ship.model_dump(by_alias=True)

    # Keys should be PascalCase
    assert set(dumped.keys()) == {"name", "vesselId"}
    assert dumped["name"] == "Evergreen"
    assert dumped["vesselId"] == "1234"


def test_ship_data_invalid_vessel_id_raises():
    # Not 4 digits
    with pytest.raises(ValidationError):
        ShipData(name="Evergreen", vessel_id="12A4")
    with pytest.raises(ValidationError):
        ShipData(name="Evergreen", vessel_id="12345")


def test_radar_data_valid_and_constraints():
    # Valid
    radar = RadarData(
        name="BARD1",
        ship_distance=12.5,
        distance_change=0.5,
        distance_status="ACTIVE",
    )
    assert radar.model_dump(by_alias=True)["name"] == "BARD1"

    # ship_distance must be >= 0 and < 100; None allowed
    RadarData(name="BCRD2", ship_distance=None, distance_change=None, distance_status="INACTIVE")

    with pytest.raises(ValidationError):
        RadarData(name="BCRD2", ship_distance=-0.1, distance_change=0.0, distance_status="ACTIVE")
    with pytest.raises(ValidationError):
        RadarData(name="BCRD2", ship_distance=100.0, distance_change=0.0, distance_status="ACTIVE")

    # distance_change must be > -100 and < 100; None allowed
    with pytest.raises(ValidationError):
        RadarData(
            name="BCRD2", ship_distance=10.0, distance_change=-100.0, distance_status="ACTIVE"
        )
    with pytest.raises(ValidationError):
        RadarData(
            name="BCRD2", ship_distance=10.0, distance_change=100.0, distance_status="ACTIVE"
        )

    # name pattern must be B[A-Z]RD[0-9]
    with pytest.raises(ValidationError):
        RadarData(name="BArd1", ship_distance=1.0, distance_change=0.0, distance_status="ACTIVE")

    # distance_status literal
    with pytest.raises(ValidationError):
        RadarData(name="BARD1", ship_distance=1.0, distance_change=0.0, distance_status="ON")


def test_hook_data_name_and_tension_bounds():
    # Valid
    h = HookData(name="Hook 12", tension=55, faulted=False, attached_line="BREAST")
    assert h.model_dump(by_alias=True)["name"] == "Hook 12"

    # Name pattern
    with pytest.raises(ValidationError):
        HookData(name="Hook 0", tension=10, faulted=False, attached_line="HEAD")
    with pytest.raises(ValidationError):
        HookData(name="Hook 100", tension=10, faulted=False, attached_line="HEAD")

    # Tension must be >= 0 and < 99; None allowed
    HookData(name="Hook 1", tension=None, faulted=True, attached_line=None)
    with pytest.raises(ValidationError):
        HookData(name="Hook 1", tension=-1, faulted=True, attached_line=None)
    with pytest.raises(ValidationError):
        HookData(name="Hook 1", tension=99, faulted=True, attached_line=None)

    # attached_line literal
    with pytest.raises(ValidationError):
        HookData(name="Hook 1", tension=10, faulted=False, attached_line="BOW")


def test_bollard_data_and_berth_data_nested_valid():
    hooks = [
        HookData(name="Hook 1", tension=10, faulted=False, attached_line="HEAD"),
        HookData(name="Hook 2", tension=20, faulted=True, attached_line="BREAST"),
    ]
    bollard = BollardData(name="BOL123", hooks=hooks)
    assert bollard.model_dump(by_alias=True)["name"] == "BOL123"

    berth = BerthData(
        name="Berth A",
        bollard_count=10,
        hook_count=27,
        ship=ShipData(name="Evergreen", vessel_id="1234"),
        radars=[
            RadarData(
                name="BARD1", ship_distance=1.2, distance_change=0.1, distance_status="ACTIVE"
            )
        ],
        bollards=[bollard],
    )

    dumped = berth.model_dump(by_alias=True)
    # Spot-check nested alias keys exist
    assert "name" in dumped and "bollardCount" in dumped and "hookCount" in dumped
    assert "ship" in dumped and "radars" in dumped and "bollards" in dumped

    # Name pattern and counts bounds
    with pytest.raises(ValidationError):
        BerthData(
            name="Berth 1",
            bollard_count=10,
            hook_count=30,
            ship=ShipData(name="Evergreen", vessel_id="1234"),
            radars=[],
            bollards=[],
        )
    with pytest.raises(ValidationError):
        BerthData(
            name="Berth A",
            bollard_count=0,
            hook_count=30,
            ship=ShipData(name="Evergreen", vessel_id="1234"),
            radars=[],
            bollards=[],
        )
    with pytest.raises(ValidationError):
        BerthData(
            name="Berth A",
            bollard_count=10,
            hook_count=0,
            ship=ShipData(name="Evergreen", vessel_id="1234"),
            radars=[],
            bollards=[],
        )


def test_port_data_full_payload_and_aliases():
    port = PortData(
        name="Port X",
        berths=[
            BerthData(
                name="Berth A",
                bollard_count=10,
                hook_count=30,
                ship=ShipData(name="Evergreen", vessel_id="1234"),
                radars=[
                    RadarData(
                        name="BARD1",
                        ship_distance=12.5,
                        distance_change=0.5,
                        distance_status="ACTIVE",
                    )
                ],
                bollards=[
                    BollardData(
                        name="BOL001",
                        hooks=[
                            HookData(
                                name="Hook 1", tension=10, faulted=False, attached_line="HEAD"
                            ),
                            HookData(
                                name="Hook 2", tension=None, faulted=True, attached_line=None
                            ),
                        ],
                    )
                ],
            )
        ],
    )

    dumped = port.model_dump(by_alias=True)
    assert set(dumped.keys()) == {"name", "berths"}
    assert isinstance(dumped["berths"], list) and dumped["berths"]


def test_tension_limits_dict_shape_and_values():
    # Check presence of known profiles
    assert "default" in TENSION_LIMITS
    assert "Berth A" in TENSION_LIMITS

    for profile, limits in TENSION_LIMITS.items():
        assert set(limits.keys()) == {"high_tension", "medium_tension", "low_tension"}, profile
        # Values should be ints and ordered high > medium > low
        hi = limits["high_tension"]
        md = limits["medium_tension"]
        lo = limits["low_tension"]
        assert all(isinstance(v, int) for v in (hi, md, lo))
        assert hi > md > lo
