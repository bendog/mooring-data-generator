from typing import Annotated, Literal, TypedDict

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field, alias_generators


class TensionLimits(TypedDict):
    high_tension: int
    medium_tension: int
    low_tension: int


TENSION_LIMITS: dict[str, TensionLimits] = {
    "default": TensionLimits(
        high_tension=24,
        medium_tension=14,
        low_tension=4,
    ),
    "Berth A": TensionLimits(
        high_tension=25,
        medium_tension=15,
        low_tension=5,
    ),
}


class BasePayloadModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=alias_generators.to_camel,
        )
    )


class ShipData(BasePayloadModel):
    name: str
    vessel_id: Annotated[str, Field(pattern=r"^[0-9]{4}$")]


class RadarData(BasePayloadModel):
    name: Annotated[str, Field(pattern=r"^B[A-Z]RD[0-9]$")]
    # Radar Should share the name of the Berth, Berth A Radar 1 = BARD1
    ship_distance: Annotated[float, Field(ge=0, lt=100)] | None
    # min 2.8 - 6.7 | max 3.4 - 30.7
    distance_change: Annotated[float, Field(gt=-100, lt=100)] | None
    # min 0.0007 - 0.06 | max 0.029 - 5.76
    distance_status: Literal["INACTIVE", "ACTIVE"]


class HookData(BasePayloadModel):
    name: Annotated[str, Field(pattern=r"^Hook [1-9][0-9]?$")]
    tension: Annotated[int, Field(ge=0, lt=99)] | None
    faulted: bool
    attached_line: Literal["BREAST", "HEAD", "SPRING", "STERN"] | None


class BollardData(BasePayloadModel):
    name: Annotated[str, Field(pattern=r"^BOL[0-9]{3}$")]
    # naming convention BOL + unique id
    hooks: list[HookData]


class BerthData(BasePayloadModel):
    name: Annotated[str, Field(pattern=r"^Berth [A-Z]$")]
    bollard_count: Annotated[int, Field(gt=0, lt=40)]  # the count of bollards: min 9 | max 15
    hook_count: Annotated[int, Field(gt=0, lt=60)]  # the count of hooks: min 27 | max 48
    ship: ShipData
    radars: list[RadarData]
    bollards: list[BollardData]


class PortData(BasePayloadModel):
    name: str  # the name of the port
    berths: list[BerthData]
