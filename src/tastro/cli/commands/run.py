from .core import Command
from ..parsers import CLParser, CommandLineInput
from ...analysis.runners import (
    ExecutionManager,
    propagation_from_source_directory,
    estimation_from_source_directory,
    prefit_analysis_from_source_directory,
)


def propagation(user_input: CommandLineInput) -> None:
    ExecutionManager(user_input.source_dirs).concurrent_execution(
        propagation_from_source_directory
    )


def estimation(user_input: CommandLineInput) -> None:
    ExecutionManager(user_input.source_dirs).concurrent_execution(
        estimation_from_source_directory
    )


def prefit(user_input: CommandLineInput) -> None:
    ExecutionManager(user_input.source_dirs).concurrent_execution(
        prefit_analysis_from_source_directory
    )


RUN_COMMANDS: list[Command] = [
    Command("propagation", CLParser, propagation, "Propagate trajectory"),
    Command("estimation", CLParser, estimation, "Perform estimation"),
    Command("prefit", CLParser, prefit, "Calculate pre-fit residuals"),
]


# def register(subparsers: "argparse._SubParsersAction[Any]") -> None:
#     register_group(subparsers, "run", "Run simulations", COMMANDS)
