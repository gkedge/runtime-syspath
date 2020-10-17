""" pytest module to tests the runtime_syspath.add_srcdirs_to_syspath module"""
import os
import re
import sys
from pathlib import Path
from typing import List

import pytest
import test_subproject_module
from test_subproject_package import test_subproject_package_mod
from test_subproject_package.test_subproject_subproject import (
    test_subproject_subproject_package_mod,
)

from runtime_syspath import add_srcdirs_to_syspath, filtered_sorted_syspath, print_syspath
from runtime_syspath.syspath_utils import inject_project_pths_to_site, persist_syspath


def test_add_srcdirs_to_syspath(root_path: Path) -> None:
    """
    Test add_srcdirs_to_syspath in runtime_syspath.syspath_utils.py module.
    """
    add_srcdirs_to_syspath()

    # Test to see if runtime_syspath's 'src' directory in now in sys.path
    src_path: Path = root_path / "src"
    src_path_str: str = os.fspath(src_path)
    sys_paths: List[str] = list()
    found_src_path: bool = False
    syspath_member: str
    for syspath_member in sys.path:
        sys_paths.append(syspath_member)
        if src_path_str == syspath_member:
            found_src_path = True
            break

    if not found_src_path:
        msg: str = f"{src_path.as_posix()} is not in:"
        syspath_mem: str
        for syspath_mem in sorted(sys_paths):
            msg += f"\n\t{Path(syspath_mem).as_posix()}"
        pytest.fail(msg)


@pytest.mark.parametrize("path_filter", [None, r"test_subproject"])
@pytest.mark.parametrize("sort", [True, False])
@pytest.mark.parametrize("no_filtering", [True, False])
def test_filtered_sorted_syspath(path_filter: str, no_filtering: bool, sort: bool) -> None:
    """ Run print_sorted_syspath. """
    paths: List[str] = filtered_sorted_syspath(
        re.compile(path_filter) if path_filter else None,
        no_filtering=no_filtering,
        sort=sort,
    )

    assert len(paths) > 0


@pytest.mark.parametrize("path_filter", [None, r"test_subproject"])
@pytest.mark.parametrize("sort", [True, False])
@pytest.mark.parametrize("no_filtering", [True, False])
def test_print_syspath(path_filter: str, no_filtering: bool, sort: bool) -> None:
    """ Run print_syspath. """
    print_syspath(
        re.compile(path_filter) if path_filter else None,
        no_filtering=no_filtering,
        sort=sort,
    )


def test_persist_syspath():
    persist_syspath(force=True)


def test_inject_project_pths_to_site():
    inject_project_pths_to_site()


def test_get_max_dots_up_to_relative_import_in_this_module() -> None:
    """
    Test get_max_dots_up_to_relative_import_in_this_module.

    :return:
    """
    assert (
        not test_subproject_module.FULLY_QUALIFIED_PACKAGE
        and not test_subproject_module.MAX_RELATIVE_IMPORT_DOTS
    )

    package = test_subproject_package_mod.FULLY_QUALIFIED_PACKAGE
    dots = test_subproject_package_mod.MAX_RELATIVE_IMPORT_DOTS
    assert package == "test_subproject_package" and dots == "."

    package = test_subproject_subproject_package_mod.FULLY_QUALIFIED_PACKAGE
    dots = test_subproject_subproject_package_mod.MAX_RELATIVE_IMPORT_DOTS
    assert package == "test_subproject_package.test_subproject_subproject" and dots == ".."

    (
        package,
        dots,
    ) = test_subproject_subproject_package_mod.number_of_dots_up_to_relatively_import_on_import()
    assert package == "test_subproject_package" and dots == "."
