import json
import logging
import random
from math import ceil

from .models import BentData, BerthData, HookData, PortData, RadarData, ShipData

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


BENT_NAMES: list[str] = [f"BNT{x:03d}" for x in range(1, 999)]

SHIP_IDS: list[str] = [f"{x:04d}" for x in range(1, 9999)]


MEAN_TENSIONS = 6
STDEV_TENSIONS = 5
MEAN_DISTANCES = 9.38
STDEV_DISTANCES = 6.73
MEAN_CHANGES = 0.68
STDEV_CHANGES = 2.6

BENT_COUNT_MIN = 9
BENT_COUNT_MAX = 15

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


def random_bent_name() -> str:
    """Return a random bent name."""
    global BENT_NAMES
    return random_single_use_choice(BENT_NAMES)


def generate_ship() -> ShipData:
    """Generate a ship data instance with unique random name and unique id"""
    global SHIP_IDS
    return ShipData(
        name=random_ship_name(),
        vessel_id=random_single_use_choice(SHIP_IDS),
    )


class HookWorker:
    """a worker class for generating and managing changes in Hook data."""

    def __init__(self, hook_number: int, attached_line: str):
        self.name: str = f"Hook {hook_number}"
        self.active: bool = random.choice([True, False, False])
        # a 5% change of being in fault state
        self.fault: bool = random.choices([True, False], weights=[0.05, 0.95])[0]
        self.attached_line = None
        self.tension = None
        if self.active:
            self.attached_line = attached_line
            self.update()

    def update(self):
        if self.active:
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


class BentWorker:
    """a worker class for managing bents and cascading data"""

    def __init__(self, bent_number: int, total_bents: int):
        self.bent_number: int = bent_number
        self.name = random_bent_name()
        self.hooks: list[HookWorker] = []
        bent_position = bent_number / total_bents
        if bent_position < 0.2:
            attached_line = "HEAD"
        elif 0.8 < bent_position:
            attached_line = "STERN"
        elif 0.4 < bent_position < 0.6:
            attached_line = "BREAST"
        else:
            attached_line = "SPRING"
        hook_count_start: int = (
            (self.bent_number * HOOK_COUNT_MULTIPLIER) - HOOK_COUNT_MULTIPLIER + 1
        )
        for hook_number in range(hook_count_start, hook_count_start + HOOK_COUNT_MULTIPLIER):
            self.hooks.append(HookWorker(hook_number, attached_line=attached_line))

    def update(self):
        """update the bent and cascading data"""
        for hook in self.hooks:
            hook.update()

    @property
    def data(self) -> BentData:
        return BentData(
            name=self.name,
            hooks=[hook.data for hook in self.hooks],
        )


class RadarWorker:
    """a worker class for generating and managing changes in Radar data."""

    def __init__(self, name: str):
        self.name: str = name
        self.active: bool = random.choice([True, False, False])
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
        self.bent_count: int = random.randint(BENT_COUNT_MIN, BENT_COUNT_MAX)
        self.hook_count: int = self.bent_count * HOOK_COUNT_MULTIPLIER
        self.ship: ShipData = generate_ship()
        self.radars: list[RadarWorker] = []
        for radar_num in range(1, random.choice([5, 6, 6, 6]) + 1):
            radar_name = f"B{berth_code}RD{radar_num}"
            self.radars.append(RadarWorker(radar_name))

        self.bents: list[BentWorker] = []
        for bent_num in range(1, self.bent_count + 1):
            self.bents.append(BentWorker(bent_num, self.bent_count))

    @property
    def name(self) -> str:
        return f"Berth {self.berth_code}"

    def update(self):
        for radar in self.radars:
            radar.update()
        for bent in self.bents:
            bent.update()

    @property
    def data(self) -> BerthData:
        return BerthData(
            name=self.name,
            bent_count=self.bent_count,
            hook_count=self.hook_count,
            ship=self.ship,
            radars=[radar.data for radar in self.radars],
            bents=[bent.data for bent in self.bents],
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
