from typing import Callable
from .core import Command
from ..parsers import (
    ResultVisualizationParser,
    ResultVisualizationInput,
    StateResidualVisualizationParser,
    StateResidualVisualizationInput,
    ParameterDistributionParser,
    ParameterDistributionInput,
)
from ...analysis.plotters.residuals import DopplerVisualizationManager
from ...analysis.plotters.orbits import StateResidualVisualizationManager
from ...analysis.plotters.statistics import (
    MatrixVisualizationManager,
    DistributionVisualizationManager,
)


def _doppler(method: str) -> Callable[[ResultVisualizationInput], None]:
    def handler(user_input: ResultVisualizationInput) -> None:
        DopplerVisualizationManager(user_input).execute_function(method)

    return handler


def _state(method: str) -> Callable[[StateResidualVisualizationInput], None]:
    def handler(user_input: StateResidualVisualizationInput) -> None:
        StateResidualVisualizationManager(user_input).execute_function(method)

    return handler


def _matrix(method: str) -> Callable[[ResultVisualizationInput], None]:
    def handler(user_input: ResultVisualizationInput) -> None:
        MatrixVisualizationManager(user_input).concurrent_execution(method)

    return handler


def state_residuals_avg(user_input: StateResidualVisualizationInput) -> None:
    StateResidualVisualizationManager(user_input).average_state_residual(
        user_input.source_dirs
    )


def state_residuals_avg_mag(
    user_input: StateResidualVisualizationInput,
) -> None:
    StateResidualVisualizationManager(
        user_input
    ).average_state_residual_magnitude(user_input.source_dirs)


def parameter_distribution(user_input: ParameterDistributionInput) -> None:
    DistributionVisualizationManager(user_input).parameter_distribution(
        user_input.source_dirs, user_input.requested, user_input.bins
    )


PLOT_COMMANDS: list[Command] = [
    # Doppler residuals
    Command(
        "doppler-prefits",
        ResultVisualizationParser,
        _doppler("pre_fit_residuals"),
        "Doppler pre-fit residuals",
    ),
    Command(
        "doppler-prefits-dist",
        ResultVisualizationParser,
        _doppler("pre_fit_residuals_with_distribution"),
        "Doppler pre-fit residuals with distribution",
    ),
    Command(
        "doppler-postfits",
        ResultVisualizationParser,
        _doppler("post_fit_residuals"),
        "Doppler post-fit residuals",
    ),
    Command(
        "doppler-postfits-dist",
        ResultVisualizationParser,
        _doppler("post_fit_residuals_with_distribution"),
        "Doppler post-fit residuals with distribution",
    ),
    Command(
        "doppler-postfits-history",
        ResultVisualizationParser,
        _doppler("post_fit_residual_history"),
        "History of Doppler post-fit residuals over iterations",
    ),
    Command(
        "doppler-residuals",
        ResultVisualizationParser,
        _doppler("residuals"),
        "Doppler pre- and post-fit residuals",
    ),
    Command(
        "doppler-residuals-dist",
        ResultVisualizationParser,
        _doppler("residuals_with_distribution"),
        "Doppler pre- and post-fit residuals with distribution",
    ),
    # State residuals
    Command(
        "state-residuals",
        StateResidualVisualizationParser,
        _state("state_residual"),
        "Residuals between two orbits",
    ),
    Command(
        "state-formal-errors",
        StateResidualVisualizationParser,
        _state("state_formal_errors"),
        "Formal errors of the estimated state",
    ),
    Command(
        "state-residuals-avg",
        StateResidualVisualizationParser,
        state_residuals_avg,
        "Average state residual across sources",
    ),
    Command(
        "state-residuals-avg-mag",
        StateResidualVisualizationParser,
        state_residuals_avg_mag,
        "Average magnitude of state residual across sources",
    ),
    # Matrices
    Command(
        "correlation",
        ResultVisualizationParser,
        _matrix("correlation_matrix"),
        "Correlation matrix",
    ),
    Command(
        "abs-correlation",
        ResultVisualizationParser,
        _matrix("absolute_correlation_matrix"),
        "Absolute value of correlation matrix",
    ),
    Command(
        "anticorrelation",
        ResultVisualizationParser,
        _matrix("anticorrelation_matrix"),
        "Anticorrelation matrix",
    ),
    Command(
        "covariance",
        ResultVisualizationParser,
        _matrix("covariance_matrix"),
        "Covariance matrix",
    ),
    # Distributions
    Command(
        "parameter-distribution",
        ParameterDistributionParser,
        parameter_distribution,
        "Distribution of an estimated parameter across sources",
    ),
]


# def register(subparsers: "argparse._SubParsersAction[Any]") -> None:
#     register_group(
#         subparsers, "plot", "Visualize results of analyses", COMMANDS
#     )
