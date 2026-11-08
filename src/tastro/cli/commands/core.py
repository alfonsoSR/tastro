from dataclasses import dataclass
from typing import Any, Callable
import argparse
from ..parsers.core import CommandLineParser


@dataclass(frozen=True)
class Command:
    """Command available as `tastro <group> <command>`

    :param name: Name typed in the terminal to run the command
    :param parser: Defines the options accepted by the command and checks their values
    :param handler: Function that performs the analysis with the options given by the user
    :param help: Short description shown by ``--help``
    """

    name: str
    parser: type[CommandLineParser[Any]]
    handler: Callable[[Any], None]
    help: str


def register_group(
    subparsers: "argparse._SubParsersAction[Any]",
    name: str,
    help: str,
    commands: list[Command],
) -> None:
    """Add a group of subcommands (e.g. ``tastro plot ...``) to the parser"""

    group = subparsers.add_parser(name, help=help, description=help)
    group_subparsers = group.add_subparsers(
        title="Subcommands", metavar="<command>", required=True
    )

    for command in commands:
        # argparse only supports a single parser class per subparsers action,
        # so we swap it before creating each subcommand
        group_subparsers._parser_class = command.parser
        subparser = group_subparsers.add_parser(
            command.name,
            help=command.help,
            description=command.help,
        )
        subparser.set_defaults(_parser=subparser, _handler=command.handler)

    return None
