""" pytest configuration for this directory (and their sub-directories)"""
import os
import sys
from pathlib import PurePath

import pytest

pytest_plugins = "pytester"  # pylint: disable=invalid-name

PROJECT_ROOT_DIR = PurePath(__file__).parent.parent


sys.path.append(os.fspath(PROJECT_ROOT_DIR / "src"))
sys.path.append(os.fspath(PROJECT_ROOT_DIR / "tests" / "test_subproject" / "src"))


@pytest.fixture(name="root_path")
def root_path_fixture() -> PurePath:
    return PROJECT_ROOT_DIR
