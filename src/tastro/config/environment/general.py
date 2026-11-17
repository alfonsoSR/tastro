from ..core import SetupBase
from .stations import StationSetup
from .vehicles import VehicleSetup
from . import planets
from pathlib import Path


class PlanetSetup(SetupBase):

    present: bool
    ephemerides: planets.PlanetEphemeridesSetup
    rotation: planets.PlanetRotationSetup
    shape: planets.PlanetShapeSetup
    gravity: planets.PlanetGravitySetup
    radiation: planets.PlanetRadiationSourceSetup
    atmosphere: planets.PlanetAtmosphereSetup
    tides: planets.SolidTideSetup


class EnvironmentGeneralSetup(SetupBase):

    global_frame_origin: str
    global_frame_orientation: str
    spacecraft: str
    center: str
    spice_kernels: list[Path]


class EnvironmentSetup(SetupBase):

    general: EnvironmentGeneralSetup
    planets: dict[str, PlanetSetup]
    stations: dict[str, StationSetup]
    vehicles: dict[str, VehicleSetup]
