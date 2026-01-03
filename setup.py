"""Build script for Cython-compiled wheels.

This setup.py is used by cibuildwheel to build wheels with compiled extensions.
For development, use `uv sync` which installs the pure Python version.
"""

import os

from setuptools import setup

# Only compile with Cython when building wheels (CIBUILDWHEEL env var is set)
# or when explicitly requested (DGKIT_COMPILE=1)
if os.environ.get("CIBUILDWHEEL") or os.environ.get("DGKIT_COMPILE"):
    from Cython.Build import cythonize

    ext_modules = cythonize(
        "src/dgkit/parsers.py",
        compiler_directives={"language_level": "3"},
    )
else:
    ext_modules = []

setup(
    ext_modules=ext_modules,
)
