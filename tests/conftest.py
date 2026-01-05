"""Fixtures for Private Repo Loader tests."""

import os
import sys


# Make custom_components importable for all tests
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

# Override _auth_url so file:// URLs work in tests
from custom_components.private_repo_loader import loader  # noqa: E402

loader._auth_url = lambda url, token: url
