""" add_srcdirs_to_syspath module. """
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Generator, List, Optional, Pattern, Set, Tuple, Union

_STD_SYSPATH_FILTER: Union[None, Pattern] = None


def init_std_syspath_filter(std_syspath_filter: Pattern) -> None:
    """
    Provide a globally bound standard filter Pattern applied to all subsequent sys.path filtering
    operations.  Note: a init_std_syspath_filter() is called from __init__.py to default to a
    globally applied pattern.
    :param std_syspath_filter: pattern to apply to all filter operations. Can be None.
    :return: None
    """
    # pylint: disable=global-statement
    global _STD_SYSPATH_FILTER
    # pylint: enable=global-statement
    _STD_SYSPATH_FILTER = std_syspath_filter


def filtered_sorted_syspath(
    path_filter: Pattern = None, no_filtering: bool = False, sort: bool = False
) -> List[str]:
    """
    Filter and sort the syspath for only paths of interest.
    :param path_filter: a pattern that the user can provide in addition to the std_syspath_filter
    :param no_filtering: allow user to not filter at all
    :param sort: allow user to sort the filtered (if filtering) sys.path
    :return: sys.path with filtering and sorting applied
    """
    paths: List[str] = sys.path
    if not no_filtering:
        if _STD_SYSPATH_FILTER:
            paths = [p for p in paths if not re.search(_STD_SYSPATH_FILTER, p)]
        if path_filter:
            paths = [p for p in paths if not re.search(path_filter, p)]

    return sorted(paths, reverse=True) if sort else paths


def print_syspath(
    path_filter: Pattern = None, no_filtering: bool = False, sort: bool = True
) -> None:
    """
    Filter and sort the syspath for only paths of interest.
    :param path_filter: a pattern that the user can provide in addition to the std_syspath_filter
    :param no_filtering: allow user to not filter at all
    :param sort: allow user to sort the filtered (if filtering) sys.path
    :return: None
    """
    paths: List[str] = filtered_sorted_syspath(path_filter, no_filtering, sort)
    print(f"\nsys.path({len(paths)} paths):")
    for path in paths:
        print(f"\t{path}")


def add_srcdirs_to_syspath() -> None:
    """
    Add all src directories under current working directory to sys.path. If CWD is not the
    project root (containing root 'src' directory), walk up ancestry to find a directory
    containing a 'src' directory. Waking up allows for being within in the 'tests' directory
    when initiating tests against modules under 'root/src'.

    Searching for 'src' directories is NOT limited to finding the '<project root>/src' (and 'src'
    directories under that '<project root>/src' directory)! All those will be found and added,
    but also any other 'src' directory found under the <project root> tree. This is desired since
    git subprojects may be anywhere (under `tests`) and their 'src' directories need to be
    included.

    :return: None
    """
    root_path: Path = Path.cwd()

    while not (root_path / "src").exists() or not (root_path / "src").is_dir():
        if not root_path.parent:
            raise RuntimeError(
                f"The CWD {Path.cwd().as_posix()} (and any parents of that path) do not contain a "
                f"'src' directory."
            )
        root_path = root_path.parent

    if root_path != Path.cwd():
        print(f"Searching for 'src' dirs from {root_path.as_posix()}")

    prior_sys_path = sys.path.copy()

    # rglob() is NOT limited to finding the <project root>/src and 'src' under that directory!
    # It will find all that, but also any other 'src' under and subdirectory level from the
    # <project root>.  This is desired since git subprojects may be anywhere (under `tests`) and
    # their 'src' directories need to be included.
    all_projects_src_dirs: Generator[Path, None, None] = root_path.rglob("src")
    for tested_src in all_projects_src_dirs:
        tested_src: Path = tested_src
        testes_src_str = str(tested_src)
        if tested_src.is_dir() and testes_src_str not in sys.path:
            sys.path.append(testes_src_str)

    diff_path_strs: Set[str] = set(prior_sys_path).symmetric_difference(set(sys.path))
    if len(diff_path_strs) > 0:
        diff_path_strs = {
            Path(diff_path_str).as_posix() for diff_path_str in diff_path_strs
        }
        print(f"Added to sys.path: {sorted(diff_path_strs)}")


def get_package_and_max_relative_import_dots(
    module_name: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Derive the fully-qualified package related to already-imported module named by 'module_name'.
    In addition, return the number of relative dots that can be used in that module before either of
    the following occur:

    ValueError: attempted relative import beyond top-level package
    ImportError: attempted relative import beyond top-level package

    :param module_name: module name of already-imported module
    :return: fully-qualified package and max relative dots.
    """
    target_module: ModuleType = sys.modules[module_name]
    dots: str = "" if not target_module.__package__ else "."
    dots: str = dots + "".join(
        "." for i in range(0, target_module.__package__.count("."))
    )
    return target_module.__package__, dots
