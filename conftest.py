"""
Pytest configuration for the War Room test suite.

Sets UTF-8 output encoding so emoji in crew.py print statements
do not crash test collection on Windows consoles.
"""

import io
import sys


def pytest_configure(config):
    """Force stdout/stderr to UTF-8 before any test runs."""
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
