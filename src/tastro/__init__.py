from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("tastro")
except PackageNotFoundError:
    pass
