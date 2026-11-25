from .core import Command
from ..parsers import ParameterTableParser, ParameterTableInput
from ...analysis.tables import show_estimated_parameters


def estimated_parameters(user_input: ParameterTableInput) -> None:
    show_estimated_parameters(
        user_input.source_dirs, user_input.refdir, user_input.formal_errors
    )


SHOW_COMMANDS: list[Command] = [
    Command(
        "estimated-parameters",
        ParameterTableParser,
        estimated_parameters,
        "Table of estimated parameters",
    ),
]
