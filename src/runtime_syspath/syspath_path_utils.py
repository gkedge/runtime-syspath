import os
import sys
from pathlib import Path, PurePath
from typing import List

PROJECT_ROOT_DIR = None


def get_project_root_dir(
    user_provided_project_root_dir: Path = None, find_dirs=(".git", "src", "tests")
) -> PurePath:
    """
    If known_root is not provided, make an attempt to figure it out the project root looking for
    a .git, src, or tests directory in the parental directories of CWD.

    :param user_provided_project_root_dir:
    :param find_dirs:
    :return:
    """
    global PROJECT_ROOT_DIR  # pylint: disable=global-statement
    PROJECT_ROOT_DIR = user_provided_project_root_dir
    if PROJECT_ROOT_DIR:
        return PROJECT_ROOT_DIR

    def find_project_root(original_test: Path, find_dirs=(".git", "src", "tests")) -> Path:
        """
        Search all parents of each dirs in succession, e.g.: all parents of for '.git' then all
        parents for 'src', etc.

        :param original_test: the directory to start looking for dirs
        :param find_dirs:
        :return: path to project root directory
        """
        home = Path.home()
        for find_dir in find_dirs:
            test = original_test
            while home != test:
                if test.is_dir() and test.glob(find_dir):
                    return test
                test = test.parent
        return original_test

    # get the top most directory path in sys.path that contains the invoker's CWD
    caller_cwd: str = os.fspath(Path.cwd())
    all_syspaths_with_cwd: List[str] = [p for p in sys.path if p in caller_cwd]
    if all_syspaths_with_cwd:
        all_syspaths_with_cwd.sort()
        caller_cwd = all_syspaths_with_cwd[0]

    PROJECT_ROOT_DIR = find_project_root(Path(caller_cwd), find_dirs=find_dirs)

    return PROJECT_ROOT_DIR
