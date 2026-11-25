from typing import Any
from .core import CommandLineParser, CommandLineInput
from pathlib import Path

DEFAULT_CANVAS_SIZE: tuple[float, float] = (6, 6)
"""Default canvas size for figures"""


class PlotterInput(CommandLineInput):

    save: bool
    show: bool
    outdir: Path
    force_outdir: bool
    name_modifier: str
    refdir: Path
    canvas_size: tuple[float, float]
    legend_columns: int
    legend_location: str
    group: bool


class ResultVisualizationInput(PlotterInput):
    """Input for plotting independent results (no comparisons)"""


class ResultComparisonInput(PlotterInput):
    """Input for comparison of results against reference"""

    reference: Path


class CommandLinePlotterParser[T: PlotterInput](CommandLineParser[T]):

    def __init__(self, **kwargs: Any) -> None:

        super().__init__(**kwargs)

        self.figures_group = self.add_argument_group("Figure processing")
        self.figures_group.add_argument(
            "-o",
            "--outdir",
            dest="outdir",
            default=".",
            help="Output directory",
        )
        self.figures_group.add_argument(
            "--force-outdir",
            dest="force_outdir",
            action="store_true",
            help="Force the program to save the plot in the directory specified through -o. Required to save plots of individual analyses in a custom directory.",
        )
        self.figures_group.add_argument(
            "--ref-dir",
            dest="refdir",
            default=".",
            help="Reference directory for the definition of labels",
        )
        self.figures_group.add_argument(
            "-s",
            "--save",
            dest="save",
            action="store_true",
            help="Save figure to file",
        )
        self.figures_group.add_argument(
            "-x",
            dest="show",
            action="store_false",
            help="Do not show the figure in an interactive window",
        )
        self.figures_group.add_argument(
            "--name-mod",
            dest="name_modifier",
            default="",
            help="Modifier for the default name of the figure",
        )
        self.figures_group.add_argument(
            "-g",
            "--group",
            dest="group",
            action="store_true",
            help="When passing multiple sources, group results into single figure",
        )

        # Modifying properties of the figure
        self.figure_properties = self.add_argument_group("Figure properties")
        self.figure_properties.add_argument(
            "--canvas-size",
            nargs=2,
            type=int,
            default=list(DEFAULT_CANVAS_SIZE),
            dest="canvas_size",
            help="Size of the figure in inches",
        )
        self.figure_properties.add_argument(
            "--legend-cols",
            default=1,
            type=int,
            dest="legend_columns",
            help="Maximum number of items per row of the legend",
        )
        self.figure_properties.add_argument(
            "--legend-loc",
            default="best",
            type=str,
            dest="legend_location",
            help="Placement of the legend",
        )

        return None

    def local_parser(
        self, defaults, arguments: dict[str, Any]
    ) -> dict[str, Any]:

        arguments = super().local_parser(defaults, arguments)

        # Define path to output directory
        outdir = Path(defaults.outdir).absolute()
        self._ensure_path_exists(outdir, "output directory")
        arguments["outdir"] = outdir

        # Define path to reference directory
        refdir = Path(defaults.refdir).absolute()
        self._ensure_path_exists(refdir, "reference directory")
        arguments["refdir"] = refdir

        # Cast canvas size
        arguments["canvas_size"] = tuple(defaults.canvas_size)

        # Arguments that do not require processing
        unprocessed_arguments: list[str] = [
            "save",
            "show",
            "name_modifier",
            "legend_columns",
            "legend_location",
            "group",
            "force_outdir",
        ]
        for argument in unprocessed_arguments:
            arguments[argument] = getattr(defaults, argument)

        return arguments


class ResultVisualizationParser(
    CommandLinePlotterParser[ResultVisualizationInput]
):

    namespace = ResultVisualizationInput


class ResultComparisonParser(CommandLinePlotterParser[ResultComparisonInput]):

    namespace = ResultComparisonInput

    def __init__(self, **kwargs: Any) -> None:

        super().__init__(**kwargs)

        # Source of reference results
        self.reference = self.add_argument_group("Reference results")
        self.reference.add_argument(
            "-r",
            "--reference",
            dest="reference",
            required=True,
            help="Source directory with reference results",
        )

        return None

    def local_parser(
        self, defaults, arguments: dict[str, Any]
    ) -> dict[str, Any]:

        arguments = super().local_parser(defaults, arguments)

        # Reference results
        reference = Path(defaults.reference).absolute()
        self._ensure_path_exists(reference, "directory with reference results")
        arguments["reference"] = reference

        return arguments


class ParameterDistributionInput(ResultVisualizationInput):

    requested: int
    bins: int


class StateResidualVisualizationInput(ResultVisualizationInput):

    reference_frame: str
    target_state: str
    reference_state: str
    formal_errors: bool = False
    show_variability: bool = True


class StateResidualComparisonInput(ResultComparisonInput):

    reference_frame: str
    target_state: str
    reference_state: str


class StateResidualVisualizationParser(
    CommandLinePlotterParser[StateResidualVisualizationInput]
):

    namespace = StateResidualVisualizationInput

    def __init__(self, **kwargs: Any) -> None:

        super().__init__(**kwargs)

        target_orbits = self.add_argument_group("Target orbits")
        target_orbits.add_argument(
            "-f",
            "--frame",
            dest="reference_frame",
            default="rsw",
            choices=["rsw", "tnw", "j2000"],
            help="Reference frame in which orbits are described",
        )
        target_orbits.add_argument(
            "-r",
            "--reference-state",
            dest="reference_state",
            choices=["pp", "pe", "ep", "ee"],
            help="Orbit to use as reference",
            required=True,
        )
        target_orbits.add_argument(
            "-t",
            "--target-state",
            dest="target_state",
            choices=["pp", "pe", "ep", "ee"],
            help="Orbit to use as target",
            required=True,
        )
        target_orbits.add_argument(
            "--formal-errors",
            dest="formal_errors",
            help="Whether to show formal errors",
            action="store_true",
        )

        self.add_argument(
            "--show-variability",
            dest="show_variability",
            action="store_true",
        )

        return None

    def local_parser(
        self, defaults, arguments: dict[str, Any]
    ) -> dict[str, Any]:

        arguments = super().local_parser(defaults, arguments)

        # Add reference frame and state configurations
        for argument in [
            "reference_frame",
            "reference_state",
            "target_state",
            "formal_errors",
            "show_variability",
        ]:
            arguments[argument] = getattr(defaults, argument)

        return arguments


class StateResidualComparisonParser(
    CommandLinePlotterParser[StateResidualComparisonInput]
):

    namespace = StateResidualComparisonInput

    def __init__(self, **kwargs: Any) -> None:

        super().__init__(**kwargs)

        # Source of reference results
        reference = self.add_argument_group("Reference results")
        reference.add_argument(
            "-r",
            dest="reference",
            required=True,
            help="Source directory with reference results",
        )

        target_orbits = self.add_argument_group("Target orbits")
        target_orbits.add_argument(
            "-f",
            "--frame",
            dest="reference_frame",
            default="rsw",
            choices=["rsw", "tnw", "j2000"],
            help="Reference frame in which orbits are described",
        )
        target_orbits.add_argument(
            "--reference-state",
            dest="reference_state",
            choices=["pp", "pe", "ep", "ee"],
            help="Orbit to use as reference",
            required=True,
        )
        target_orbits.add_argument(
            "--target-state",
            dest="target_state",
            choices=["pp", "pe", "ep", "ee"],
            help="Orbit to use as target",
            required=True,
        )

        return None

    def local_parser(
        self, defaults, arguments: dict[str, Any]
    ) -> dict[str, Any]:

        arguments = super().local_parser(defaults, arguments)

        # Parse directory with reference results
        reference = Path(defaults.reference).absolute()
        self._ensure_path_exists(reference, "directory with reference results")
        arguments["reference"] = reference

        # Add reference frame and state configurations
        for argument in [
            "reference_frame",
            "reference_state",
            "target_state",
        ]:
            arguments[argument] = getattr(defaults, argument)

        return arguments


class ParameterDistributionParser(
    CommandLinePlotterParser[ParameterDistributionInput]
):

    namespace = ParameterDistributionInput

    def __init__(self, **kwargs: Any) -> None:

        super().__init__(**kwargs)

        self.add_argument(
            "--requested",
            dest="requested",
            required=True,
            help="Index of the requested parameter",
        )
        self.add_argument(
            "-b",
            dest="bins",
            help="Number of bins",
            default=5,
        )

        return None

    def local_parser(
        self, defaults, arguments: dict[str, Any]
    ) -> dict[str, Any]:

        arguments = super().local_parser(defaults, arguments)
        arguments["requested"] = int(defaults.requested)
        arguments["bins"] = int(defaults.bins)

        return arguments
