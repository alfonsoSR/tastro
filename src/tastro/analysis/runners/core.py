from pathlib import Path
from ...config import CaseSetup
from tudatpy.data_input.environment_data import spice
from ...environment import system_of_bodies_from_config
from ...propagation import (
    translational_propagator_settings_from_config,
    propagate_translational_dynamics,
)
from ...estimation import perform_estimation, perform_prefit_analysis
from ...logging import log, log_to_file
from typing import Callable
import multiprocessing as mp
from ...io import EstimationResults, load_kernel_list


class ExecutionManager:
    """Runs the same task for several source directories, in parallel when
    there is more than one

    :param source_dirs: Directories containing configuration and results
    """

    def __init__(self, source_dirs: list[Path]) -> None:

        # Save source directories
        self.source_dirs: list[Path] = source_dirs

        return None

    def concurrent_execution(self, function: Callable) -> None:

        if len(self.source_dirs) > 1:
            with mp.Pool() as pool:
                pool.map(function, self.source_dirs)
        else:
            function(self.source_dirs[0])

        return None


@log_to_file("tpropagator.log")
def propagation_from_source_directory(source_dir: Path) -> None:
    """Propagate trajectory from configuration in source directory"""

    # Define paths to configuration file and metakernel
    config_path: Path = source_dir / "configuration.yaml"
    metak_path: Path = source_dir / "metak.tm"

    # Load configuration
    config = CaseSetup.from_config_file(config_path)
    config.perform_propagation = True

    try:

        # Load SPICE kernels in configuration file
        load_kernel_list(config, metak_path)
        # for kernel in config.environment.general.spice_kernels:
        #     log.debug(f"Loading kernel: {kernel}")
        #     spice.load_kernel(str(kernel))

        # log.fatal(spice.get_total_count_of_kernels_loaded())

        # # Load contents of metakernel
        # spice.load_kernel(str(metak_path))

        # Define system of bodies and propagation settings
        system_of_bodies = system_of_bodies_from_config(config=config)
        propagator_settings = translational_propagator_settings_from_config(
            config=config,
            bodies=system_of_bodies,
        )

        # Propagate translational dynamics
        propagation_results = propagate_translational_dynamics(
            bodies=system_of_bodies,
            propagator=propagator_settings,
            config=config,
        )

        # Save output to file
        propagation_results.save_to_file(source_dir / "results.pkl")

    finally:
        # Clear kernel pool
        spice.clear_kernels()

    return None


@log_to_file("testimator.log")
def estimation_from_source_directory(source_dir: Path) -> None:
    """Run estimation analysis from configuration in source directory

    Estimations from synthetic observations are handled by independent functions

    :param source_dir: Path to the directory containing the configuration
    """

    # Define paths to configuration, metakernel, and propagation results
    config_path: Path = source_dir / "configuration.yaml"
    metak_path: Path = source_dir / "metak.tm"

    # Load configuration
    config = CaseSetup.from_config_file(config_path)
    config.perform_estimation = True

    try:
        # Load SPICE kernels in configuration file
        load_kernel_list(config, metak_path)
        # for kernel in config.environment.general.spice_kernels:
        #     log.debug(f"Loading kernel: {kernel}")
        #     spice.load_kernel(str(kernel))
        # # Load contents of metakernel
        # spice.load_kernel(str(metak_path))

        # Define system of bodies and propagation settings
        system_of_bodies = system_of_bodies_from_config(config=config)
        propagator_settings = translational_propagator_settings_from_config(
            config=config,
            bodies=system_of_bodies,
        )

        # Perform estimation analysis
        estimation_results = perform_estimation(
            bodies=system_of_bodies,
            propagator=propagator_settings,
            config=config,
        )

        # Save output to file
        estimation_results.save_to_file(source_dir / "estimation.pkl")

    finally:
        # Clear kernel pool
        spice.clear_kernels()

    return None


@log_to_file("tprefit.log")
def prefit_analysis_from_source_directory(source_dir: Path) -> None:

    # Define paths to configuration file and metakernel
    config_path: Path = source_dir / "configuration.yaml"
    metak_path: Path = source_dir / "metak.tm"

    # Load configuration
    config = CaseSetup.from_config_file(config_path)
    config.perform_estimation = True

    try:
        # # Load metakernel
        # spice.load_kernel(str(metak_path))
        # Load SPICE kernels in configuration file
        # for kernel in config.environment.general.spice_kernels:
        #     log.debug(f"Loading kernel: {kernel}")
        #     spice.load_kernel(str(kernel))
        load_kernel_list(config, metak_path)

        # Ensure vehicle has ephemerides
        vehicle_name = config.environment.general.spacecraft
        vehicle_config = config.environment.vehicles[vehicle_name]
        if not vehicle_config.ephemerides.present:
            log.warning(f"Forcing {vehicle_name} to have ephemerides")
            vehicle_config.ephemerides.present = True

        # Create system of bodies and estimation manager
        bodies = system_of_bodies_from_config(config)

        # Calculate pre-fit residuals
        prefit_results = perform_prefit_analysis(bodies, config)

        # Save output to file
        log.info(f"Saving results of pre-fit analysis")
        prefit_results.save_to_file(source_dir / "prefit_results.pkl")

    finally:
        spice.clear_kernels()

    return None


def covariance_analysis_from_source_directory(source_dir: Path) -> None:

    # Load estimation results
    estimation = EstimationResults.from_file(source_dir / "estimation.pkl")

    # Load configuration
    config = CaseSetup.from_config_file(source_dir / "configuration.yaml")
    config.perform_estimation = True

    try:
        spice.load_kernel(str(source_dir / "metak.tm"))

    finally:
        spice.clear_kernels()

    return None


# class RunnerManager[T: "CommandLineInput"]:
#     """Manager for propagation, estimation, and pre-fit analyses"""

#     def __init__(self, user_input: T) -> None:

#         # Save source directories
#         self.source_dirs: list[Path] = user_input.source_dirs

#         return None

#     def concurrent_execution(self, function: Callable) -> None:

#         if len(self.source_dirs) > 1:
#             with mp.Pool() as pool:
#                 pool.map(function, self.source_dirs)
#         else:
#             function(self.source_dirs[0])

#         return None
