from dataclasses import dataclass
from pathlib import Path
import numpy as np
from ...io import EstimationResults
from ...logging import log
from ..plotters.statistics import get_parameter_labels_from_source

NAME_HEADER: str = "Configuration"
"""Header of the column with the names of the configurations"""

COLUMN_SEPARATOR: str = "  "
"""Separation between columns of the tables"""


@dataclass
class EstimatedParameters:
    """Estimated parameters of a single analysis

    :param name: Name of the configuration
    :param labels: Plain text labels of the estimated parameters
    :param values: Final values of the estimated parameters
    :param formal_errors: Formal errors of the estimated parameters
    """

    name: str
    labels: list[str]
    values: np.ndarray
    formal_errors: np.ndarray


def get_configuration_name(source: Path, refdir: Path) -> str:
    """Name of a configuration: path relative to refdir if possible"""

    try:
        return str(source.relative_to(refdir))
    except ValueError:
        return str(source)


def load_parameters(source: Path, refdir: Path) -> EstimatedParameters:
    """Load estimated parameters and formal errors from source directory"""

    estimation = EstimationResults.from_file(source / "estimation.pkl")
    labels = get_parameter_labels_from_source(source, latex=False)
    values = np.asarray(estimation.final_parameters)
    formal_errors = np.sqrt(np.diag(estimation.covariance_matrix))

    if len(labels) != len(values):
        log.fatal(
            f"Inconsistent number of labels ({len(labels)}) and estimated "
            f"parameters ({len(values)}) in {source}"
        )
        exit(1)

    return EstimatedParameters(
        get_configuration_name(source, refdir), labels, values, formal_errors
    )


def check_consistent_labels(entries: list[EstimatedParameters]) -> None:
    """Ensure all analyses estimate the same set of parameters"""

    expected = entries[0]
    for entry in entries[1:]:
        if entry.labels != expected.labels:
            log.fatal(
                f"Estimated parameters of {entry.name} "
                f"({', '.join(entry.labels)}) differ from those of "
                f"{expected.name} ({', '.join(expected.labels)})"
            )
            exit(1)

    return None


def _value_cell(value: float, error: float | None, signed: bool) -> str:

    cell = f"{value:+.6e}" if signed else f"{value:.6e}"
    if error is not None:
        cell += f" +/- {error:.2e}"
    return cell


def _relative_cell(difference: float, reference: float) -> str:

    if reference == 0.0:
        return "-"
    return f"{100.0 * difference / abs(reference):+.3e} %"


def _column_widths(rows: list[list[str]]) -> list[int]:

    return [max(len(row[idx]) for row in rows) for idx in range(len(rows[0]))]


def _render(rows: list[list[str]], widths: list[int]) -> str:
    """Render rows of cells: first column left-aligned, rest right-aligned"""

    lines: list[str] = []
    for row in rows:
        cells = [row[0].ljust(widths[0])] + [
            cell.rjust(width) for cell, width in zip(row[1:], widths[1:])
        ]
        lines.append(COLUMN_SEPARATOR.join(cells).rstrip())

    return "\n".join(lines)


def format_show_table(
    entries: list[EstimatedParameters], formal_errors: bool
) -> str:
    """Table with one row per analysis showing its estimated parameters"""

    rows: list[list[str]] = [[NAME_HEADER] + entries[0].labels]
    for entry in entries:
        rows.append(
            [entry.name]
            + [
                _value_cell(value, error if formal_errors else None, False)
                for value, error in zip(entry.values, entry.formal_errors)
            ]
        )

    return _render(rows, _column_widths(rows))


def format_comparison_table(
    reference: EstimatedParameters,
    entries: list[EstimatedParameters],
    formal_errors: bool,
    relative_error: bool,
) -> str:
    """Table with reference values and differences of each analysis"""

    header = [NAME_HEADER] + reference.labels

    reference_row = [reference.name] + [
        _value_cell(value, error if formal_errors else None, False)
        for value, error in zip(reference.values, reference.formal_errors)
    ]

    difference_rows: list[list[str]] = []
    for entry in entries:
        differences = entry.values - reference.values
        difference_rows.append(
            [entry.name]
            + [
                _value_cell(diff, error if formal_errors else None, True)
                for diff, error in zip(differences, entry.formal_errors)
            ]
        )
        if relative_error:
            difference_rows.append(
                [""]
                + [
                    _relative_cell(diff, ref)
                    for diff, ref in zip(differences, reference.values)
                ]
            )

    widths = _column_widths([header, reference_row] + difference_rows)

    return "\n".join(
        [
            _render([header], widths),
            "Reference values",
            _render([reference_row], widths),
            "Difference with respect to reference",
            _render(difference_rows, widths),
        ]
    )


def show_estimated_parameters(
    sources: list[Path], refdir: Path, formal_errors: bool
) -> None:

    entries = [load_parameters(source, refdir) for source in sources]
    check_consistent_labels(entries)
    print(format_show_table(entries, formal_errors))

    return None


def compare_estimated_parameters(
    reference_source: Path,
    sources: list[Path],
    refdir: Path,
    formal_errors: bool,
    relative_error: bool,
) -> None:

    reference = load_parameters(reference_source, refdir)
    entries = [load_parameters(source, refdir) for source in sources]
    check_consistent_labels([reference] + entries)
    print(
        format_comparison_table(
            reference, entries, formal_errors, relative_error
        )
    )

    return None
