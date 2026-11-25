import argparse
from importlib_metadata import version
from .commands.compare import COMPARISON_COMMANDS
from .commands.plot import PLOT_COMMANDS
from .commands.run import RUN_COMMANDS
from .commands.show import SHOW_COMMANDS
from .commands.core import register_group
from ..config import InternalResources


def main() -> None:
    """Command-line interface for the `tastro` command"""

    # Initialize parser
    tastro_parser = argparse.ArgumentParser(
        prog="tastro",
        description="Top level interface to perform analyses, generate plots with their outputs and perform comparisons",
    )
    tastro_parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Show version of the library and exit.",
    )

    # Add subparsers
    # https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_subparsers
    subparsers = tastro_parser.add_subparsers(
        title="Subcommands",
        required=False,  # Needed to allow for --version
        metavar="<command>",
    )

    # There is one submodule for each subcommand, and they all contain a
    # `register` function. This function takes
    register_group(
        subparsers,
        "run",
        "Perform an analysis",
        RUN_COMMANDS,
    )

    # Register functions for plotting
    register_group(
        subparsers,
        "plot",
        "Visualize results of analyses",
        PLOT_COMMANDS,
    )

    # Register functions for displaying results in the terminal
    register_group(
        subparsers,
        "show",
        "Display results of analyses in the terminal",
        SHOW_COMMANDS,
    )

    # Register functions for comparison
    register_group(
        subparsers,
        "compare",
        "Perform comparisons between outputs or analyses",
        COMPARISON_COMMANDS,
    )

    # Read input from command line
    arguments = tastro_parser.parse_args()

    # If requested, show version and exit
    if arguments.version:
        print(f"tastro {version("tastro")}")
        return None

    # If called without subcommand, print help and return
    if not hasattr(arguments, "_parser"):
        tastro_parser.print_help()
        return None

    # Otherwise
    parser = arguments._parser
    user_input = parser.namespace(**parser.local_parser(arguments, {}))
    arguments._handler(user_input)

    return None
