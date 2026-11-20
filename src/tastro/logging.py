import logging
from pathlib import Path
from typing import Callable, Iterator
import contextlib
import ctypes
import functools
import json
import os
import subprocess
import sys

GREY = "\x1b[38;20m"
BLUE = "\x1b[34;20m"
GREEN = "\x1b[32;20m"
YELLOW = "\x1b[33;20m"
RED = "\x1b[31;20m"
BOLD_RED = "\x1b[31;1m"
RESET = "\x1b[0m"
FORMAT = "%(levelname)-8s :: %(asctime)s :: %(message)s"
EXCEPTION_FORMAT = "\n"


class Formatter(logging.Formatter):

    _FORMATS: dict[int, str] | None = None

    @property
    def FORMATS(self) -> dict[int, str]:

        if self._FORMATS is None:
            raise NotImplementedError(
                f"Formats not set for {type(self).__name__}"
            )

        return self._FORMATS

    def format(self, record) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class FileFormatter(Formatter):

    _FORMATS = {
        logging.DEBUG: FORMAT,
        logging.INFO: FORMAT,
        logging.WARNING: FORMAT,
        logging.ERROR: FORMAT,
        logging.CRITICAL: FORMAT,
    }


class StdoutFormatter(Formatter):

    _FORMATS = {
        logging.DEBUG: GREEN + FORMAT + RESET,
        logging.INFO: BLUE + FORMAT + RESET,
        logging.WARNING: YELLOW + FORMAT + RESET,
        logging.ERROR: RED + FORMAT + RESET,
        logging.CRITICAL: BOLD_RED + FORMAT + RESET,
    }


class FileHandler(logging.FileHandler):

    @staticmethod
    def from_path_and_level(filename: Path, level: str) -> "FileHandler":

        handler = FileHandler(str(filename), mode="w")
        handler.setLevel(level)
        handler.setFormatter(FileFormatter())

        return handler


class AlternativeFileHandler(logging.StreamHandler):

    @staticmethod
    def from_buffer_and_level(buffer, level: str) -> "AlternativeFileHandler":

        handler = AlternativeFileHandler(buffer)
        handler.setLevel(level)
        handler.setFormatter(FileFormatter())

        return handler


class StdoutHandler(logging.StreamHandler):

    @staticmethod
    def from_level(level: str) -> "StdoutHandler":

        handler = StdoutHandler(stream=sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(StdoutFormatter())

        return handler


log = logging.getLogger(__package__)
log.setLevel(logging.DEBUG)


# Markers used to send tastro's log records through the captured stdout pipe:
# RECORD_START + levelname + LEVEL_END + message, with newlines in the message
# replaced by NEWLINE so that each record occupies a single line
_RECORD_START = "\x1e"
_LEVEL_END = "\x1f"
_NEWLINE = "\x1d"

# Code executed by the helper process that writes captured output to the log
# file and the terminal. It runs in a separate interpreter (standard library
# only) so that it keeps reading while the main process is busy in C++ code
# holding the GIL, which would otherwise block on a full pipe. It is the only
# writer of the log file, so the output is recorded in the order it arrives.
_STREAM_FORWARDER = """
import json, os, selectors, sys, time

log_path, out_fd, err_fd = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
colors, reset = json.loads(sys.argv[4]), sys.argv[5]
record_start, level_end, newline = sys.argv[6], sys.argv[7], sys.argv[8]
ready_fd = int(sys.argv[9])
raw_level = {out_fd: ("INFO", "stdout"), err_fd: ("WARNING", "stderr")}

log_file = open(log_path, "w", errors="replace")
terminal = open(1, "w", errors="replace", closefd=False)

def emit(level, text):
    for handle, line in (
        (log_file, text),
        (terminal, colors.get(level, "") + text + reset),
    ):
        try:
            handle.write(line + "\\n")
            handle.flush()
        except (OSError, ValueError):
            pass

def process(fd, line):
    line = line.rstrip()
    if not line:
        return
    if line.startswith(record_start):
        level, _, message = line[1:].partition(level_end)
        emit(level, message.replace(newline, "\\n"))
    else:
        level, tag = raw_level[fd]
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        emit(level, f"{level:<8} :: {stamp} :: [{tag}] {line}")

selector = selectors.DefaultSelector()
buffers = {}
for fd in (out_fd, err_fd):
    selector.register(fd, selectors.EVENT_READ)
    buffers[fd] = b""

# Signal the parent process that output can be redirected
os.write(ready_fd, b"1")
os.close(ready_fd)

while selector.get_map():
    for key, _ in selector.select():
        fd = key.fd
        chunk = os.read(fd, 4096)
        if not chunk:
            selector.unregister(fd)
            if buffers[fd]:
                process(fd, buffers[fd].decode(errors="replace"))
            buffers[fd] = b""
            continue
        *lines, buffers[fd] = (buffers[fd] + chunk).split(b"\\n")
        for line in lines:
            process(fd, line.decode(errors="replace"))

log_file.close()
"""


@functools.cache
def _libc() -> ctypes.CDLL | None:
    try:
        return ctypes.CDLL(None)
    except OSError:
        return None


def _flush_std_streams() -> None:
    """Flush Python and C-level buffers of stdout and stderr

    Output written by tudat through std::cout goes through C stdio, so its
    buffers must be flushed explicitly before redirecting or restoring the
    underlying file descriptors.
    """

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (AttributeError, ValueError):
            pass

    libc = _libc()
    if libc is not None:
        libc.fflush(None)

    return None


def _line_buffer_c_stdout() -> None:
    """Make C stdout line buffered, so that tudat's output is forwarded as it
    is produced instead of in blocks of several kB (default for pipes)"""

    libc = _libc()
    if libc is None:
        return None

    try:
        c_stdout = ctypes.c_void_p.in_dll(libc, "stdout")
        libc.setvbuf.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_size_t,
        ]
        libc.setvbuf(c_stdout, None, 1, 0)  # 1 == _IOLBF
    except (ValueError, AttributeError):
        pass

    return None


class CapturedStdoutHandler(logging.Handler):
    """Writes log records to the captured stdout, so that they are recorded by
    the forwarder process in order with the rest of the output"""

    def __init__(self, level: str) -> None:
        super().__init__(level)
        self.setFormatter(FileFormatter())
        return None

    def emit(self, record: logging.LogRecord) -> None:

        try:
            message = self.format(record).replace("\n", _NEWLINE)
            # Leading newline terminates any partial line printed before
            payload = (
                f"\n{_RECORD_START}{record.levelname}{_LEVEL_END}{message}\n"
            ).encode("utf-8", errors="replace")

            # Write pending output first to preserve ordering
            _flush_std_streams()
            while payload:
                payload = payload[os.write(1, payload) :]

        except Exception:
            self.handleError(record)

        return None


@contextlib.contextmanager
def capture_std_streams(log_path: Path) -> Iterator[None]:
    """Redirect stdout and stderr of the process to a log file

    Redirection happens at the file-descriptor level, so output written by
    C/C++ extensions (e.g. tudat) is captured along with Python output. Lines
    written to stdout are recorded as INFO and lines written to stderr as
    WARNING, both in the log file and in the terminal. Records emitted with a
    `CapturedStdoutHandler` are recorded with their original level.

    :param log_path: Path to the log file (overwritten)
    """

    _flush_std_streams()

    # Duplicate original descriptors so that they can be restored
    saved_out = os.dup(1)
    saved_err = os.dup(2)
    out_read, out_write = os.pipe()
    err_read, err_write = os.pipe()
    ready_read, ready_write = os.pipe()

    # Start helper process that forwards captured lines to file and terminal
    colors = {
        "DEBUG": GREEN,
        "INFO": BLUE,
        "WARNING": YELLOW,
        "ERROR": RED,
        "CRITICAL": BOLD_RED,
    }
    forwarder = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-c",
            _STREAM_FORWARDER,
            str(log_path),
            str(out_read),
            str(err_read),
            json.dumps(colors),
            RESET,
            _RECORD_START,
            _LEVEL_END,
            _NEWLINE,
            str(ready_write),
        ],
        stdin=subprocess.DEVNULL,
        stdout=saved_out,
        stderr=saved_err,
        pass_fds=(out_read, err_read, ready_write),
    )
    os.close(out_read)
    os.close(err_read)
    os.close(ready_write)

    # Wait until the forwarder is reading, so that no backlog of output builds
    # up (lines from different pipes can only be ordered if read promptly)
    os.read(ready_read, 1)
    os.close(ready_read)

    # Redirect stdout and stderr to the pipes, line buffered so that output
    # reaches the forwarder as soon as each line is complete
    _line_buffer_c_stdout()
    python_line_buffering = getattr(sys.stdout, "line_buffering", None)
    if python_line_buffering is False:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]
    os.dup2(out_write, 1)
    os.dup2(err_write, 2)
    os.close(out_write)
    os.close(err_write)

    try:
        yield None

    finally:
        # Restore original descriptors: closes the write ends of the pipes
        _flush_std_streams()
        if python_line_buffering is False:
            sys.stdout.reconfigure(line_buffering=False)  # type: ignore[union-attr]
        os.dup2(saved_out, 1)
        os.dup2(saved_err, 2)
        os.close(saved_out)
        os.close(saved_err)

        # Wait until all captured output has been written
        forwarder.wait()


def log_to_file(file_name: str) -> Callable:

    def log_to_file_decorator(function: Callable) -> Callable:

        @functools.wraps(function)
        def function_inner(source_dir: Path, *args, **kwargs):

            # Define output file for logging
            output_file = source_dir / f"{file_name}"

            # Capture stdout/stderr (including tudat's) and log records
            with capture_std_streams(output_file):

                handler = CapturedStdoutHandler("DEBUG")
                log.addHandler(handler)

                try:
                    return function(source_dir, *args, **kwargs)
                except Exception:
                    log.exception(
                        f"Unhandled exception in {function.__name__}"
                    )
                    raise
                finally:
                    log.removeHandler(handler)

        return function_inner

    return log_to_file_decorator
