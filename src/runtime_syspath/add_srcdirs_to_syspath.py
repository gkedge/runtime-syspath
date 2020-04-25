""" add_srcdirs_to_syspath module. """
import sys

from pathlib import Path
from typing import Generator, Set


def add_srcdirs_to_syspath() -> None:
    """
    Add all src directories under current working directory to sys.path. If CWD is not the
    project root (containing root 'src' directory), walk up ancestry to find a directory
    containing a 'src' directory. Waking up allows for being within in the 'tests' directory
    when initiating tests against modules under 'root/src'.

    Searching for 'src' directories is NOT limited to finding the '<project root>/src' (and 'src'
    directies under that '<project root>/src' directory! All those will be found and added,
    but also any other 'src' directory found under the <project root> tree. This is desired since
    git subprojects may be anywhere (under `tests`) and their 'src' directories need to be
    included.

    :return: None
    """
    root_path: Path = Path.cwd()

    while not (root_path / 'src').exists() or not (root_path / 'src').is_dir():
        if not root_path.parent:
            raise RuntimeError(f"The CWD {Path.cwd().as_posix()} (and any parents of that path) do "
                               f"not contain a 'src' directory.")
        root_path = root_path.parent

    if root_path != Path.cwd():
        print(f"Searching for 'src' dirs from {root_path.as_posix()}")

    prior_sys_path = sys.path.copy()

    # rglob() is NOT limited to finding the <project root>/src and 'src' under that directory!
    # It will find all that, but also any other 'src' under and subdirectory level from the
    # <project root>.  This is desired since git subprojects may be anywhere (under `tests`) and
    # their 'src' directories need to be included.
    all_projects_src_dirs: Generator[Path, None, None] = root_path.rglob('src')
    for tested_src in all_projects_src_dirs:
        tested_src: Path = tested_src
        testes_src_str = str(tested_src)
        if tested_src.is_dir() and testes_src_str not in sys.path:
            sys.path.append(testes_src_str)

    diff_path_strs: Set[str] = set(prior_sys_path).symmetric_difference(set(sys.path))
    if len(diff_path_strs) > 0:
        diff_path_strs = {Path(diff_path_str).as_posix() for diff_path_str in diff_path_strs}
        print(f'Added to sys.path: {sorted(diff_path_strs)}')
