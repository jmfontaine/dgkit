"""Build script for mypyc-compiled wheels.

This setup.py is used by cibuildwheel to build wheels with compiled extensions.
For development, use `uv sync` which installs the pure Python version.
"""

import os

from setuptools import setup

# Only compile with mypyc when building wheels (CIBUILDWHEEL env var is set)
# or when explicitly requested (DGKIT_COMPILE=1)
if os.environ.get("CIBUILDWHEEL") or os.environ.get("DGKIT_COMPILE"):
    from mypyc.build import mypycify

    ext_modules = mypycify(
        [
            "src/dgkit/parsers.py",
        ],
        opt_level="3",
        debug_level="1",
    )
else:
    ext_modules = []

setup(
    ext_modules=ext_modules,
)
