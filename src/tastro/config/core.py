import typing
import types
from ..logging import log
from tudatpy.astro import time_representation as ttime
import numpy as np
import traceback
from ..core import AutoDataclass
from dataclasses import dataclass
from pathlib import Path
import tomllib

RESOURCES_FILE: str = ".tastro.toml"


@dataclass
class InternalResources:

    kernels: Path
    resources: Path
    observations: Path

    @staticmethod
    def load_raw_resources(path: Path) -> dict[str, Path]:
        """Loads resources from specified file"""

        log.debug(f"Loading internal resources from {path}")

        # Load complete contents
        with path.open("rb") as buffer:
            content = tomllib.load(buffer)

        # FUTURE: Control version

        # Load and validate paths
        paths_dict: dict[str, Path] = {}
        for key, value in content["paths"].items():
            current_path = Path(value)
            if not current_path.exists():
                log.error(
                    f"Resources file {path} contains invalid path to {key}: "
                    f"{current_path}. Directory does not exist."
                )
                exit(1)
            if not current_path.is_dir():
                log.error(
                    f"Resources file {path} contains invalid path to {key}: "
                    f"{current_path}. Not a directory."
                )
                exit(1)
            paths_dict[key.lower()] = current_path

        return paths_dict

    @classmethod
    def from_resources_file(cls) -> "InternalResources":
        """Loads paths to internal resources from standard file

        Paths to internal resources are specified in the [paths] section of a resources file (i.e. `.tastro.toml`). This function searches for a resources file and, if found, uses it to extract the paths to the resources. The function checks if the paths exist and fails otherwise.

        The program tries to find the file in the current directory first. If not present, it looks in the home directory of the current user. If not present, it fails and requests the user to create the file.

        :return: InternalResources object containing the paths to the directories with resources.
        """

        # Try to load resources from current directory
        cwd_file = Path().cwd() / RESOURCES_FILE
        if cwd_file.exists():
            return cls(**InternalResources.load_raw_resources(cwd_file))

        # Try to load resources from HOME
        home_file = Path().home() / RESOURCES_FILE
        if home_file.exists():
            return cls(**InternalResources.load_raw_resources(home_file))
        else:
            log.error(
                f"Failed to find a valid {RESOURCES_FILE}. Please, create one either in the current directory or in `{home_file.parent}` using the template in the `config` directory of our GitHub repository."
            )
            exit(1)


class SetupBase(metaclass=AutoDataclass):

    @staticmethod
    def __type_is_enumeration(_type) -> bool:

        # Ensure __members__ is present
        if not hasattr(_type, "__members__"):
            return False

        # Get first item in __members__
        member = list(getattr(_type, "__members__").values())[0]

        # If not of the same type as _type, not an enumeration
        if not isinstance(member, _type):
            return False

        return True

    @classmethod
    def __process_single_attribute(cls, name: str, target_type, value):

        # Initialize from raw if possible
        if hasattr(target_type, "from_raw"):
            log.debug(f"Initializing from raw: {name} - {target_type}")
            return getattr(target_type, "from_raw")(value)

        # Avoid casting None when a parameter is not set
        if value is None:

            # Return None if target type is not container
            if not isinstance(target_type, types.GenericAlias):
                return value

            # Return empty containers instead of None
            target_type_name = str(target_type).split("[")[0]
            if target_type_name == "list":
                return []
            elif target_type_name == "dict":
                return {}
            else:
                raise NotImplementedError("Invalid generic alias")

        # Handle casting of ISO string epoch to Time object
        if (target_type is ttime.Time) and isinstance(value, str):
            log.debug(
                f"Casting ISO string to Time object: {name} - {target_type}"
            )
            return ttime.DateTime.from_iso_string(value).to_epoch_time_object()

        # Handle enumerations
        if cls.__type_is_enumeration(target_type):
            log.debug(f"Initializing enumeration: {name} - {target_type}")

            # Fail if value is not an option
            if value not in getattr(target_type, "__members__"):
                log.error(
                    f"Invalid option {value} for enumeration {target_type}"
                )
                exit(1)

            return getattr(target_type, value)

        # Handle numpy arrays
        if (target_type is np.ndarray) and isinstance(value, list):
            log.debug(f"Initializing numpy array: {name} - {target_type}")
            return np.array(value)

        # Handle paths relative to resources
        if (
            (target_type is Path)
            and isinstance(value, str)
            and value.startswith("$TASTRO_")
        ):
            # Isolate the placeholder and the type of resource
            complete_placeholder = value.split("/")[0]
            resource_type = complete_placeholder.split("_")[-1].lower()

            # Retrieve path to internal resource
            resources = InternalResources.from_resources_file()
            resource = getattr(resources, resource_type)

            # Expand path and return
            expanded_path = resource / "/".join(value.split("/")[1:])
            log.debug(f"Expanded path: {value} >>> {expanded_path}")
            return expanded_path

        # Otherwise, initialize with constructor
        log.debug(f"Initializing from constructor: {name} - {target_type}")
        return target_type(value)

    @classmethod
    def __process_attribute(cls, name: str, value: typing.Any):

        # Get type of attribute from annonation
        argtype = cls.__annotations__[name]

        # Check if the attribute is a value, or a collection of values
        if not isinstance(argtype, types.GenericAlias):

            return cls.__process_single_attribute(name, argtype, value)

        # Process dictionary of values
        if isinstance(value, dict):

            # Get desired type for values
            __value_type = argtype.__args__[-1]

            # Generate dictionary with processed single values
            return {
                key: cls.__process_single_attribute(key, __value_type, _val)
                for key, _val in value.items()
            }

        # Process list of values
        if isinstance(value, list):

            # Get desired type for values
            __value_type = argtype.__args__[0]

            # Generate list with processed single values
            return [
                cls.__process_single_attribute(
                    f"Item {idx} of {name}", __value_type, item
                )
                for idx, item in enumerate(value)
            ]

        # Take care of errors in __process_single_attribute
        return cls.__process_single_attribute(name, argtype, value)

    @classmethod
    def from_raw(
        cls, raw_configuration: dict[str, typing.Any] | None
    ) -> "typing.Self":

        # Initialize dictionary with arguments of the class
        kwargs: dict[str, typing.Any] = {}

        # If raw configuration is dictionary, initialize based on it
        if isinstance(raw_configuration, dict):

            for raw_key, raw_value in raw_configuration.items():

                # Make key lowercase
                argname: str = raw_key.lower()

                # Ignore item if data structure is not available
                if argname not in cls.__annotations__:
                    log.warning(
                        f"Ignoring attribute {argname} of {cls.__name__}"
                        f" :: Data structure is not available"
                    )
                    continue

                # Process item
                kwargs[argname] = cls.__process_attribute(argname, raw_value)

        # Handle case in which section is missing from configuration file
        elif raw_configuration is None:

            # Try to mark as not present (all fields will be None)
            if "present" in getattr(cls, "__dataclass_fields__"):
                kwargs["present"] = False
            else:
                log.fatal(
                    "Missing field in configuration could not be marked "
                    f"as not present :: {cls.__name__}"
                )
                exit(1)

        else:

            log.fatal(
                f"Invalid type for raw_configuration: {type(raw_configuration)}"
            )
            exit(1)

        # Fill missing arguments setting them to None
        for expected_kwarg in cls.__annotations__:

            # Identify missing arguments for class constructor
            if expected_kwarg not in kwargs:

                # Get expected type of argument
                expected_type = cls.__annotations__[expected_kwarg]

                # If the expected type has from_raw, process
                if hasattr(expected_type, "from_raw"):
                    kwargs[expected_kwarg] = getattr(expected_type, "from_raw")(
                        None
                    )
                    continue

                # If argument has a default value, use default
                if expected_kwarg in cls.__dict__:
                    continue

                # Set argument to None and raise warning
                log.warning(f"Setting {expected_kwarg} to None : {cls}")
                kwargs[expected_kwarg] = None

        return cls(**kwargs)

    def __getattribute__(self, name: str):

        # Use method of base class to get value of argument
        value = super().__getattribute__(name)

        # Indicates that argument is missing/not set in configuration file
        if value is None:

            out = traceback.extract_stack()

            log.error(
                f"Parameter {name} not set in configuration file"
                f" :: {self.__class__.__name__}"
            )
            log.error(f"Source :: {out[-2]}")
            exit(1)

        return value
