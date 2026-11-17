from tudatpy.data_input.environment_data import spice
from pathlib import Path
from ..logging import log
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import CaseSetup


def load_kernel_list(
    config: "CaseSetup", metakernel_path: Path | None = None
) -> None:

    try:
        kernels = config.environment.general.spice_kernels
    except SystemExit:
        if metakernel_path is None:
            log.error(
                "Missing metakernel with configuration file without kernel list"
            )
            exit(1)
        kernels = [metakernel_path]

    for kernel in kernels:
        log.debug(f"Loading kernel: {kernel}")
        spice.load_kernel(str(kernel))

    return None
