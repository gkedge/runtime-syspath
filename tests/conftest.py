""" pytest configuration for this directory (and their sub-directories)"""
import sys
from pathlib import Path

import pytest


# None of this kind of work find the root or append 'src' dirs to the 'sys.path' need be
# performed by conftest.py's or main()'s using the runtime_syspath::add_srcdirs_to_syspath
# function. This is only necessary for testing that function.
def get_root_path() -> Path:
    """
    If CWD is not the project root (containing root 'src' directory), walk up prior to start
    adding 'src' directories from that point down. This allows for being within in the 'tests'
    directory when initiating tests against modules under 'root/src'.
    :return: root path
    """
    # pylint: disable=redefined-outer-name
    root_path: Path = Path.cwd()
    while not (root_path / 'src').exists() or not (root_path / 'src').is_dir():
        print(f'Root path: {root_path}')
        if not root_path.parent:
            raise RuntimeError(f"{Path.cwd().as_posix()} and any parents of that path contain a "
                               f"'src' directory.")
        root_path = root_path.parent
    return root_path


sys.path.append(str(get_root_path() / 'src'))


@pytest.fixture
def root_path() -> Path:
    """
    Fixtures can't be called directly so get_root_path() can't be a fixture.  Just a wrapper.
    :return:
    """
    return get_root_path()
