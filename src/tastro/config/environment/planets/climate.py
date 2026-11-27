from ...core import SetupBase


class MarsClimateDatabaseClimateSettings(SetupBase):

    dust_scenario: int
    perturbation_key: int
    perturbation_seed: float
    gravity_wave_length: float
    high_resolution_mode: int
    max_cache_size: int
    present: bool = False


class PlanetClimateSetup(SetupBase):

    present: bool
    model: str
    mars_climate_database_settings: MarsClimateDatabaseClimateSettings
