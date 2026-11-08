"""Command line interface of tastro.

The ``tastro`` command is defined in :mod:`tastro.cli.main`. Argument parsers
and the typed inputs they produce live in :mod:`tastro.cli.parsers`.

This module must not import :mod:`tastro.cli.commands`: the analysis code
imports :mod:`tastro.cli.parsers`, and the commands import the analysis code.
"""
