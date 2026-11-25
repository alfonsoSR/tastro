from typing import Any
from pathlib import Path
from .core import CommandLineParser, CommandLineInput


class ParameterTableInput(CommandLineInput):
    """Input for tables of estimated parameters"""

    formal_errors: bool
    refdir: Path


class ParameterComparisonInput(ParameterTableInput):
    """Input for comparison of estimated parameters against reference"""

    reference: Path
    relative_error: bool


class _ParameterTableParserBase[T: ParameterTableInput](CommandLineParser[T]):

    def __init__(self, **kwargs: Any) -> None:

        super().__init__(**kwargs)

        self.table_group = self.add_argument_group("Table options")
        self.table_group.add_argument(
            "--formal-errors",
            dest="formal_errors",
            action="store_true",
            help="Show formal errors alongside the estimated parameters",
        )
        self.table_group.add_argument(
            "--ref-dir",
            dest="refdir",
            default=".",
            help="Reference directory for the definition of configuration names",
        )

        return None

    def local_parser(
        self, defaults, arguments: dict[str, Any]
    ) -> dict[str, Any]:

        arguments = super().local_parser(defaults, arguments)

        # Define path to reference directory for names
        refdir = Path(defaults.refdir).absolute()
        self._ensure_path_exists(refdir, "reference directory")
        arguments["refdir"] = refdir

        arguments["formal_errors"] = defaults.formal_errors

        return arguments


class ParameterTableParser(_ParameterTableParserBase[ParameterTableInput]):

    namespace = ParameterTableInput


class ParameterComparisonParser(
    _ParameterTableParserBase[ParameterComparisonInput]
):

    namespace = ParameterComparisonInput

    def __init__(self, **kwargs: Any) -> None:

        super().__init__(**kwargs)

        self.table_group.add_argument(
            "--relative-error",
            dest="relative_error",
            action="store_true",
            help="Show difference with respect to reference as relative error in percentage",
        )

        reference = self.add_argument_group("Reference results")
        reference.add_argument(
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

        reference = Path(defaults.reference).absolute()
        self._ensure_path_exists(reference, "directory with reference results")
        arguments["reference"] = reference

        arguments["relative_error"] = defaults.relative_error

        return arguments
