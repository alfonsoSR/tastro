from typing import Callable
from .core import Command
from ..parsers import (
    ResultComparisonParser,
    ResultComparisonInput,
    StateResidualComparisonParser,
    StateResidualComparisonInput,
    ParameterComparisonParser,
    ParameterComparisonInput,
)

from ...analysis.tables import compare_estimated_parameters
from ...analysis.plotters.residuals import DopplerComparisonManager
from ...analysis.plotters.orbits import StateResidualComparisonManager
from ...analysis.plotters.statistics import MatrixComparisonManager


def _doppler(method: str) -> Callable[[ResultComparisonInput], None]:
    def handler(user_input: ResultComparisonInput) -> None:
        DopplerComparisonManager(user_input).execute_function(method)

    return handler


def _matrix(method: str) -> Callable[[ResultComparisonInput], None]:
    def handler(user_input: ResultComparisonInput) -> None:
        MatrixComparisonManager(user_input).concurrent_execution(method)

    return handler


def state_residuals(user_input: StateResidualComparisonInput) -> None:
    StateResidualComparisonManager(user_input).execute_function(
        "state_residual"
    )


def state_differences(user_input: StateResidualComparisonInput) -> None:
    StateResidualComparisonManager(user_input).execute_function("state_vector")


def estimated_parameters(user_input: ParameterComparisonInput) -> None:
    compare_estimated_parameters(
        user_input.reference,
        user_input.source_dirs,
        user_input.refdir,
        user_input.formal_errors,
        user_input.relative_error,
    )


COMPARISON_COMMANDS: list[Command] = [
    Command(
        "doppler-prefits",
        ResultComparisonParser,
        _doppler("pre_fit_residuals"),
        "Difference in Doppler pre-fit residuals",
    ),
    Command(
        "doppler-postfits",
        ResultComparisonParser,
        _doppler("post_fit_residuals"),
        "Difference in Doppler post-fit residuals",
    ),
    Command(
        "doppler-residuals",
        ResultComparisonParser,
        _doppler("residuals"),
        "Difference in Doppler pre- and post-fit residuals",
    ),
    Command(
        "state-residuals",
        StateResidualComparisonParser,
        state_residuals,
        "Difference in state residuals",
    ),
    Command(
        "state-vectors",
        StateResidualComparisonParser,
        state_differences,
        "Difference between trajectories from different analyses",
    ),
    Command(
        "correlation",
        ResultComparisonParser,
        _matrix("correlation_matrix"),
        "Difference in correlation matrices",
    ),
    Command(
        "abs-correlation",
        ResultComparisonParser,
        _matrix("absolute_correlation_matrix"),
        "Difference in absolute correlation matrices",
    ),
    Command(
        "rel-abs-correlation",
        ResultComparisonParser,
        _matrix("relative_difference_absolute_correlation"),
        "Relative difference in absolute correlation matrices",
    ),
    Command(
        "estimated-parameters",
        ParameterComparisonParser,
        estimated_parameters,
        "Difference in estimated parameters with respect to reference",
    ),
]


# def register(subparsers: "argparse._SubParsersAction[Any]") -> None:
#     register_group(
#         subparsers,
#         "compare",
#         "Perform comparisons between outputs",
#         COMMANDS,
#     )
