from .core import SetupBase
from .environment import EnvironmentSetup
from .propagation import PropagationSetup
from .estimation import EstimationSetup
from tudatpy.astro import time_representation as ttime
from pathlib import Path
import yaml
from ..logging import log


class SimulationIntervalSetup(SetupBase):

    initial_epoch: ttime.Time
    final_epoch: ttime.Time


class CaseSetup(SetupBase):

    time: SimulationIntervalSetup
    environment: EnvironmentSetup
    propagation: PropagationSetup
    estimation: EstimationSetup

    perform_estimation: bool = False
    perform_propagation: bool = False
    evaluate_accelerations: bool = False

    base_directory: Path | None = None

    @classmethod
    def from_config_file(cls, config_path: Path) -> "CaseSetup":

        log.info(f"Loading configuration from {config_path}")

        raw_config = yaml.safe_load(config_path.open("r"))
        output = cls.from_raw(raw_config)

        # Set base directory
        output.base_directory = config_path.parent

        log.info(f"Finished loading configuration")

        return output

    def propagation_start_epoch(self) -> ttime.Time:
        """Epoch at which the propagation starts, as defined in the configuration

        :return: Start epoch of the propagation
        """

        match self.propagation.integrator.general.starting_point:

            case "start":
                return self.time.initial_epoch

            case "end":
                return self.time.final_epoch

            case "middle":

                duration = self.time.final_epoch - self.time.initial_epoch
                return self.time.initial_epoch + duration / 2.0

            case "custom":

                custom_epoch = (
                    self.propagation.integrator.general.custom_start_epoch
                )
                if custom_epoch is None:
                    raise ValueError("Custom propagation epoch not specified")

                return custom_epoch

            case _:
                raise NotImplementedError("Invalid propagation start option")

    @staticmethod
    def propagation_start_epoch_from_file(config_file: Path) -> ttime.Time:
        """Epoch at which the propagation starts, read directly from a
        configuration file

        Only the values needed to find the epoch are read, so the rest of the
        file does not need to match the current format of the configuration.

        :param config_file: Path to the configuration file
        :return: Start epoch of the propagation
        """

        # Load raw contents of configuration file
        with config_file.open("rb") as buffer:
            raw_config = yaml.safe_load(buffer)

        # Extract information about the starting point of the propagation
        integrator_config = raw_config["Propagation"]["integrator"]["general"]
        starting_point = integrator_config["starting_point"]
        initial_epoch = ttime.DateTime.from_iso_string(
            raw_config["Time"]["initial_epoch"]
        ).to_epoch_time_object()
        final_epoch = ttime.DateTime.from_iso_string(
            raw_config["Time"]["final_epoch"]
        ).to_epoch_time_object()
        del raw_config

        # Find propagation start epoch based on configuration
        match starting_point:

            case "start":
                return initial_epoch
            case "end":
                return final_epoch
            case "middle":
                duration = final_epoch - initial_epoch
                return initial_epoch + (duration / 2.0)
            case "custom":
                if integrator_config["custom_start_epoch"] is None:
                    raise ValueError("Custom propagation epoch not specified")
                return ttime.DateTime.from_iso_string(
                    integrator_config["custom_start_epoch"]
                ).to_epoch_time_object()
            case _:
                raise NotImplementedError("Invalid propagation start option")
