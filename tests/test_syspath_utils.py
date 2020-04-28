""" pytest module to tests the runtime_syspath.add_srcdirs_to_syspath module"""
import re
import sys
from pathlib import Path
from typing import List

import pytest

from runtime_syspath import __version__, add_srcdirs_to_syspath, filtered_sorted_syspath, \
    print_syspath


def test_version() -> None:
    """
    Test version string in runtime_syspath.__init__.py
    """
    assert __version__ == '0.1.0'


def test_add_srcdirs_to_syspath(root_path: Path) -> None:
    """
    Test add_srcdirs_to_syspath in runtime_syspath.syspath_utils.py module.
    """
    add_srcdirs_to_syspath()

    # Test to see if runtime_syspath's 'src' directory in now in sys.path
    src_path: Path = root_path / 'src'
    src_path_str: str = str(src_path)
    sys_paths: List[str] = list()
    found_src_path: bool = False
    for syspath_member in sys.path:
        sys_paths.append(syspath_member)
        if src_path_str == syspath_member:
            found_src_path = True
            break

    if not found_src_path:
        msg: str = f'{src_path.as_posix()} is not in:'
        for syspath_mem in sorted(sys_paths):
            msg += f'\n\t{Path(syspath_mem).as_posix()}'
        pytest.fail(msg)


@pytest.mark.parametrize("path_filter", [None, r'test_subproject'])
@pytest.mark.parametrize("sort", [True, False])
@pytest.mark.parametrize("no_filtering", [True, False])
def test_filtered_sorted_syspath(path_filter: str, no_filtering: bool, sort: bool):
    """ Run print_sorted_syspath. """
    paths: List[str] = filtered_sorted_syspath(re.compile(path_filter) if path_filter else None,
                                               no_filtering=no_filtering, sort=sort)

    assert len(paths) > 0


@pytest.mark.parametrize("path_filter", [None, r'test_subproject'])
@pytest.mark.parametrize("sort", [True, False])
@pytest.mark.parametrize("no_filtering", [True, False])
def test_print_syspath(path_filter: str, no_filtering: bool, sort: bool):
    """ Run print_syspath. """
    print_syspath(re.compile(path_filter) if path_filter else None,
                  no_filtering=no_filtering, sort=sort)
