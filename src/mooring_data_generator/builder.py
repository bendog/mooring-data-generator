import json
import logging
import random
import sys
from math import ceil

from .models import BerthData, BollardData, HookData, PortData, RadarData, ShipData

if sys.version_info < (3, 13):
    # if batched doesn't exist, reinvent it.
    from itertools import islice

    def batched(iterable, n, *args, **kwargs):
        if n < 1:
            raise ValueError("n must be at least one")
        iterator = iter(iterable)
        while batch := tuple(islice(iterator, n)):
            yield batch
else:
    from itertools import batched


logger = logging.getLogger(__name__)

# A list of well-known Western Australian port names
WA_PORT_NAMES: list[str] = [
    "Port Hedland",
    "Dampier",
    "Fremantle",
    "Kwinana",
    "Bunbury",
    "Esperance",
    "Albany",
    "Geraldton",
    "Broome",
    "Wyndham",
    "Derby",
    "Carnarvon",
]


NAUTICAL_SUPERLATIVES: list[str] = [
    "Majestic",
    "Sovereign",
    "Resolute",
    "Valiant",
    "Vigilant",
    "Dauntless",
    "Liberty",
    "Enduring",
    "Gallant",
    "Noble",
    "Guardian",
    "Intrepid",
    "Courageous",
    "Steadfast",
    "Regal",
    "Stalwart",
    "Indomitable",
    "Invincible",
    "Triumphant",
    "Victorious",
    "Glorious",
    "Fearless",
    "Mighty",
    "Bold",
    "Brave",
    "Formidable",
    "Relentless",
    "Valorous",
    "Audacious",
    "Diligent",
    "Implacable",
    "Indefatigable",
    "Prosperous",
    "Seaborne",
    "Seagoing",
    "Oceanic",
    "Maritime",
    "Coastal",
    "Pelagic",
    "Windward",
    "Leeward",
    "Tempestuous",
    "Sturdy",
]

NAUTICAL_BASE_NAMES: list[str] = [
    # Western
    "Amelia",
    "Charlotte",
    "Olivia",
    "Sophia",
    "Emily",
    "Grace",
    # East Asian
    "Hana",
    "Mei",
    "Yuna",
    "Sakura",
    "Aiko",
    "Keiko",
    # South Asian
    "Asha",
    "Priya",
    "Anika",
    "Riya",
    "Sana",
    "Neha",
    # Southeast Asian
    "Linh",
    "Thao",
    "Trang",
    "Ngoc",
    "Anh",
    "Nicha",
    # Latin (Spanish/Portuguese/LatAm)
    "Camila",
    "Valentina",
    "Isabela",
    "Gabriela",
    "Lucia",
    "Paula",
]


BOLLARD_NAMES: list[str] = [f"BOL{x:03d}" for x in range(1, 999)]

SHIP_IDS: list[str] = [f"{x:04d}" for x in range(1, 9999)]


MEAN_TENSIONS = 6
STDEV_TENSIONS = 5
MEAN_DISTANCES = 9.38
STDEV_DISTANCES = 6.73
MEAN_CHANGES = 0.68
STDEV_CHANGES = 2.6

BOLLARD_COUNT_MIN = 9
BOLLARD_COUNT_MAX = 15
MEAN_BOLLARD_COUNT = 12
STDEV_BOLLARD_COUNT = 2.2

HOOK_COUNT_MULTIPLIER = 3


def random_single_use_choice(list_of_strings: list[str]) -> str:
    """Source a one-time random string from a list of strings"""
    random_str = random.choice(list_of_strings)
    list_of_strings.remove(random_str)
    return random_str


def random_ship_name() -> str:
    """Generate a random ship name by combining a nautical superlative with a potential ship name.

    The format will be "<Superlative> <Name>". Example: "Majestic Amelia" or "Valiant Sophia".
    """
    global NAUTICAL_SUPERLATIVES
    global NAUTICAL_BASE_NAMES
    return f"{random_single_use_choice(NAUTICAL_SUPERLATIVES)} {random_single_use_choice(NAUTICAL_BASE_NAMES)}"


def random_wa_port_name() -> str:
    """Return a random Western Australian port name.
    Preventing the option from being selected in the future."""
    global WA_PORT_NAMES
    return random_single_use_choice(WA_PORT_NAMES)


def random_bollard_name() -> str:
    """Return a random bollard name."""
    global BOLLARD_NAMES
    return random_single_use_choice(BOLLARD_NAMES)


def generate_ship() -> ShipData:
    """Generate a ship data instance with unique random name and unique id"""
    global SHIP_IDS
    return ShipData(
        name=random_ship_name(),
        vessel_id=random_single_use_choice(SHIP_IDS),
    )


def line_name_generator(bollard_list: list[int]) -> list[str]:
    """return a list of which lines will be used for which bollards"""
    response: list[str] = []
    for bollard_number in bollard_list:
        bollard_position = bollard_number / len(bollard_list)
        if bollard_position < 0.25:
            attached_line = "HEAD"
        elif 0.83 < bollard_position:
            attached_line = "STERN"
        elif 0.4 < bollard_position < 0.65:
            attached_line = "BREAST"
        else:
            attached_line = "SPRING"
        response.append(attached_line)
    return response


HookStatus = bool | None

HooksStatuses = tuple[HookStatus, ...]

BollardStructure = list[tuple[int, str, HooksStatuses]]


def random_bollard_structure(bollard_count: int) -> BollardStructure:
    """build a balanced random bollard structure"""
    bollard_number_list: list[int] = list(range(1, bollard_count + 1))
    bollard_line_name_list: list[str] = line_name_generator(bollard_number_list)
    hooks_active_list: list[tuple[bool | None, ...]] = list(
        batched(
            random.choices(
                (True, False, None),
                weights=(5, 4, 0.5),
                k=len(bollard_number_list) * HOOK_COUNT_MULTIPLIER,
            ),
            3,
            strict=True,
        )
    )
    # Check hooks
    # line_status_count: dict[str, dict[str, int]] = {
    #     line_name: {"True": 0, "False": 0, "None": 0} for line_name in set(bollard_line_name_list)
    # }
    # for idx, hook_status in enumerate(hooks_active_list):
    #     line_name: str = bollard_line_name_list[idx]
    #     line_status_count[line_name]["True"] += len([x for x in hook_status if x is True])
    #     line_status_count[line_name]["False"] += len([x for x in hook_status if x is False])
    #     line_status_count[line_name]["None"] += len([x for x in hook_status if x is None])

    # TODO: perhaps the first hook for a new type of line is always true?

    bollard_and_hook_structure: BollardStructure = list(
        zip(bollard_number_list, bollard_line_name_list, hooks_active_list, strict=True)
    )
    return bollard_and_hook_structure


class HookWorker:
    """a worker class for generating and managing changes in Hook data."""

    def __init__(self, hook_number: int, hook_status: HookStatus, attached_line: str):
        self.name: str = f"Hook {hook_number}"
        self.active: bool = True if hook_status is True else False
        # a 5% change of being in fault state
        self.fault: bool = True if hook_status is None else False
        self.attached_line = None
        self.tension = None
        if self.active:
            self.attached_line = attached_line
            self.update()

    def update(self):
        if self.active and not self.fault:
            self.tension = abs(ceil(random.gauss(MEAN_CHANGES, STDEV_CHANGES)))

    @property
    def data(self) -> HookData:
        # noinspection PyTypeChecker
        return HookData(
            name=self.name,
            tension=self.tension,
            faulted=self.fault,
            attached_line=self.attached_line,
        )


class BollardWorker:
    """a worker class for managing bollards and cascading data"""

    def __init__(self, bollard_number: int, attached_line: str, hook_statuses: HooksStatuses):
        self.bollard_number: int = bollard_number
        self.name = random_bollard_name()
        self.hooks: list[HookWorker] = []
        hook_count_start: int = (
            (self.bollard_number * HOOK_COUNT_MULTIPLIER) - HOOK_COUNT_MULTIPLIER + 1
        )
        hook_numbers = range(hook_count_start, hook_count_start + HOOK_COUNT_MULTIPLIER)

        for hook_number, hook_status in zip(hook_numbers, hook_statuses, strict=True):
            self.hooks.append(HookWorker(hook_number, hook_status, attached_line=attached_line))

    def update(self):
        """update the bollard and cascading data"""
        for hook in self.hooks:
            hook.update()

    @property
    def data(self) -> BollardData:
        return BollardData(
            name=self.name,
            hooks=[hook.data for hook in self.hooks],
        )


class RadarWorker:
    """a worker class for generating and managing changes in Radar data."""

    def __init__(self, name: str, active: bool):
        self.name: str = name
        self.active: bool = active
        self.distance: float | None = None
        self.change: float | None = None
        if self.active:
            self.distance: float = abs(random.gauss(MEAN_DISTANCES, STDEV_DISTANCES))
            self.change: float = abs(random.gauss(MEAN_CHANGES, STDEV_CHANGES))

    def update(self) -> tuple[float, float]:
        if self.active:
            new_distance: float = abs(random.gauss(MEAN_TENSIONS, STDEV_TENSIONS))
            new_change: float = abs(self.distance - new_distance)
            self.distance = new_distance
            self.change = new_change
        return self.distance, self.change

    @property
    def data(self) -> RadarData:
        # noinspection PyTypeChecker
        return RadarData(
            name=self.name,
            ship_distance=self.distance,
            distance_change=self.change,
            distance_status="ACTIVE" if self.active else "INACTIVE",
        )


class BerthWorker:
    """a worker class for generating and managing changes in Berth data."""

    def __init__(self, berth_code: str):
        self.berth_code: str = berth_code
        # self.bollard_count: int = random.randint(BOLLARD_COUNT_MIN, BOLLARD_COUNT_MAX)
        self.bollard_count: int = ceil(random.gauss(MEAN_BOLLARD_COUNT, STDEV_BOLLARD_COUNT))
        self.hook_count: int = self.bollard_count * HOOK_COUNT_MULTIPLIER
        self.ship: ShipData = generate_ship()
        self.radars: list[RadarWorker] = []
        radar_number_list: list[int] = list(range(1, random.choice([5, 6, 6, 6]) + 1))
        radar_active_list: list[bool] = random.choices(
            [True, False], weights=(2, 1), k=len(radar_number_list)
        )
        radars: list[tuple[int, bool]] = list(
            zip(radar_number_list, radar_active_list, strict=True)
        )
        for radar_num, radar_active in radars:
            radar_name = f"B{berth_code}RD{radar_num}"
            self.radars.append(RadarWorker(radar_name, radar_active))

        self.bollards: list[BollardWorker] = []

        for bollard_num, bollard_line, hook_structure in random_bollard_structure(
            self.bollard_count
        ):
            self.bollards.append(BollardWorker(bollard_num, bollard_line, hook_structure))

    @property
    def name(self) -> str:
        return f"Berth {self.berth_code}"

    def update(self):
        for radar in self.radars:
            radar.update()
        for bollard in self.bollards:
            bollard.update()

    @property
    def data(self) -> BerthData:
        return BerthData(
            name=self.name,
            bollard_count=self.bollard_count,
            hook_count=self.hook_count,
            ship=self.ship,
            radars=[radar.data for radar in self.radars],
            bollards=[bollard.data for bollard in self.bollards],
        )


class PortWorker:
    """a worker class for generating and managing change of ports"""

    def __init__(self):
        self.name: str = random_wa_port_name()
        self.berth_count: int = random.randint(1, 8)
        self.berths: list[BerthWorker] = []
        for berth_num in range(1, self.berth_count + 1):
            berth_code: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[berth_num]
            self.berths.append(BerthWorker(berth_code))

    def update(self):
        for berth in self.berths:
            berth.update()

    @property
    def data(self) -> PortData:
        return PortData(
            name=self.name,
            berths=[berth.data for berth in self.berths],
        )


def build_random_port() -> PortWorker:
    """Construct a `PortData` instance with a random WA port name."""
    return PortWorker()


def main() -> None:
    """Generate a single random WA port and print it as JSON."""
    port = build_random_port()
    # Use Pydantic's by_alias to apply PascalCase field names from BasePayloadModel
    payload = port.data.model_dump(by_alias=True)
    logger.info(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
