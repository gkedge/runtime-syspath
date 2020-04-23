import sys

from pathlib import Path
from typing import Generator, Set


def add_srcdirs_to_syspath():
    all_projects_src_dirs: Generator[Path, None, None] = Path.cwd().rglob('src')
    prior_sys_path = sys.path.copy()
    for tested_src in all_projects_src_dirs:
        tested_src: Path = tested_src
        testes_src_str = str(tested_src)
        if tested_src.is_dir() and testes_src_str not in sys.path:
            sys.path.append(testes_src_str)

    diff_path_strs: Set[str] = set(prior_sys_path).symmetric_difference(set(sys.path))
    diff_path_strs = {Path(diff_path_str).as_posix() for diff_path_str in diff_path_strs}
    print(f'Added to sys.path: {sorted(diff_path_strs)}')
