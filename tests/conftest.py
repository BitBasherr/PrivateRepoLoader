import os
import sys

# Make custom_components importable for all tests
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)
