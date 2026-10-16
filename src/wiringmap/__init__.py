"""wiringmap: see how your code is wired. Offline, interactive, AI optional."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("wiringmap")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0"
