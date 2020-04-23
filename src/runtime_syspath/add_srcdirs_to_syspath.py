""" add_srcdirs_to_syspath module. """
import sys

from pathlib import Path
from typing import Generator, Set


def add_srcdirs_to_syspath() -> None:
    """
    Add all src directories under current working directory to sys.path. If CWD is not the
    project root (containing root 'src' directory), walk up prior to start # adding 'src'
    directories from that point down. This allows for being within in the 'tests' # directory
    when initiating tests against modules under 'root/src'.
    :return: None
    """
    root_path: Path = Path.cwd()

    while not (root_path / 'src').exists() or not (root_path / 'src').is_dir():
        if not root_path.parent:
            raise RuntimeError(f"{Path.cwd().as_posix()} and any parents of that path do not "
                               f"contain a 'src' directory.")
        root_path = root_path.parent

    if root_path != Path.cwd():
        print(f"Searching for 'src' dirs from {root_path.as_posix()}")

    all_projects_src_dirs: Generator[Path, None, None] = root_path.rglob('src')
    prior_sys_path = sys.path.copy()
    for tested_src in all_projects_src_dirs:
        tested_src: Path = tested_src
        testes_src_str = str(tested_src)
        if tested_src.is_dir() and testes_src_str not in sys.path:
            sys.path.append(testes_src_str)

    diff_path_strs: Set[str] = set(prior_sys_path).symmetric_difference(set(sys.path))
    if len(diff_path_strs) > 0:
        diff_path_strs = {Path(diff_path_str).as_posix() for diff_path_str in diff_path_strs}
        print(f'Added to sys.path: {sorted(diff_path_strs)}')
