""" syspath_utils module. """
import os
import re
import sys
from itertools import chain
from pathlib import Path, PurePath
from shutil import rmtree
from string import Template
from types import ModuleType
from typing import Dict, Generator, List, Optional, Pattern, Set, Tuple, Union

from .syspath_path_utils import get_project_root_dir
from .syspath_sleuth import get_customize_path

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
    Filter and sort the sys.path for only paths of interest.
    :param path_filter: a pattern that the user can provide in addition to the std_syspath_filter
    :param no_filtering: allow user to not filter at all
    :param sort: allow user to sort the filtered (if filtering) sys.path
    :return: sys.path with filtering and sorting applied
    """
    paths: List[str] = sys.path
    if not no_filtering:
        path: str
        if _STD_SYSPATH_FILTER:
            paths = [path for path in paths if not re.search(_STD_SYSPATH_FILTER, path)]
        if path_filter:
            paths = [path for path in paths if not re.search(path_filter, path)]

    return sorted(paths, reverse=True) if sort else paths


def print_syspath(
    path_filter: Pattern = None, no_filtering: bool = False, sort: bool = True
) -> None:
    """
    Filter and sort the sys.path for only paths of interest.
    :param path_filter: a pattern that the user can provide in addition to the std_syspath_filter
    :param no_filtering: allow user to not filter at all
    :param sort: allow user to sort the filtered (if filtering) sys.path
    :return: None
    """
    paths: List[str] = filtered_sorted_syspath(path_filter, no_filtering, sort)
    print(f"\nsys.path({len(paths)} paths):")
    path: str
    for path in paths:
        print(f"\t{path}")


def persist_syspath(
    user_provided_project_root_dir: Path = None, force: bool = False, path_filter: Pattern = None
) -> None:
    """
    Persist a set of ordered [000-999]*.pth.template files that represent each
    project-related entry in the sys.path. The files are persisted into the
    /pathto/projectroot/pths directory. If caller did not supply the /pathto/projectroot via
    'user_provided_project_root_dir', attempt to determine that.

    :param user_provided_project_root_dir: root of project using persist_syspath()
    :param force: for directory creation
    :param path_filter: a pattern that the user can provide in addition to the std_syspath_filter
    :return: None
    """
    root_dir: PurePath = (
        user_provided_project_root_dir if user_provided_project_root_dir else get_project_root_dir()
    )

    persist_dir: Path = Path(root_dir / "pths")

    if not persist_dir.exists():
        create = force or input(f"Create {persist_dir}? [y,n] ").strip().lower().startswith("y")
        if create:
            persist_dir.mkdir(mode=0o766)

    for path in persist_dir.glob("**/*"):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            rmtree(path)

    paths: List[str] = filtered_sorted_syspath(path_filter)
    for index in range(0, len(paths)):
        path_str = sys.path[index]
        if path_str.startswith(os.fspath(root_dir)):
            pth_path = Path(path_str)
            relative_pth = pth_path.relative_to(root_dir)
            persist_path = Path(
                persist_dir,
                f"{index:03d}_{root_dir.stem}_"
                f"{os.fspath(relative_pth).replace(os.sep, '_')}.pth.template",
            )

            if not persist_path.exists():
                with persist_path.open("x") as persist_path_f:
                    # Write template that can be converted to wherever a project's clones are
                    # rooted using inject_project_pths_to_site()
                    persist_path_f.write(
                        f"${{path_to_project}}{os.sep}"
                        f"{os.fspath(pth_path.relative_to(root_dir))}\n"
                    )


def inject_project_pths_to_site(user_provided_project_root_dir: PurePath = None) -> None:
    """
    Iterate through all templates in /pathto/projectroot/pths converting the templates to
    the paths rooted to the current /pathto/projectroot. If caller did not supply the
    /pathto/projectroot via 'user_provided_project_root_dir', attempt to determine that.

    :param user_provided_project_root_dir: root of project using inject_project_pths_to_site()
    """
    root_dir: PurePath = (
        user_provided_project_root_dir if user_provided_project_root_dir else get_project_root_dir()
    )

    persist_dir: Path = Path(root_dir / "pths")

    if not persist_dir.exists():
        print(f"No pth templates found within {os.fspath(persist_dir)}")
        return

    customize_path, _ = get_customize_path()
    site_path = customize_path.parent
    # glob in all the files in the site into a list. Remove from the list each one that is still
    # relevant; delete all that remain in the list that are no longer used.
    project_site_pths: List[Path] = list(site_path.glob(f"[0-9][0-9][0-9]_{root_dir.stem}_*.pth"))
    site_pth_map: Dict[str, Path] = {}
    for project_site_pth in project_site_pths:
        with project_site_pth.open() as project_site_pth_f:
            sys_path_entry_parts: Tuple[str, ...] = PurePath(project_site_pth_f.read()).parts
            index = sys_path_entry_parts.index(root_dir.stem) + 1
            sys_path_entry = os.sep.join(sys_path_entry_parts[index:])
            if sys_path_entry in site_pth_map:
                print(f"{sys_path_entry} represented; deleting {project_site_pth}")
                project_site_pth.unlink()
            else:
                site_pth_map.update({sys_path_entry: project_site_pth})

    substitution_map: Dict[str, str] = {"path_to_project": os.fspath(root_dir)}
    templates_paths: List[Path] = list(persist_dir.glob("*.pth.template"))
    templates_paths.sort()

    filled_in_path_to_file_map: Dict[str, str] = {}
    template_path: Path
    for template_path in templates_paths:
        template_filename = template_path.name
        with template_path.open() as template_f:
            template_str = template_f.read().strip()
        template_str_fragment = template_str[len("${path_to_project}/") :]

        filled_in_path = Template(template_str).substitute(substitution_map)
        if filled_in_path in filled_in_path_to_file_map:
            print(
                f"{template_filename}'s {filled_in_path} already represented with "
                f"{filled_in_path_to_file_map[filled_in_path]}.\n\tDeleting {template_filename}"
            )
            template_path.unlink()
            continue

        filled_in_path_to_file_map.update({filled_in_path: template_filename})

        site_pth_path: Path = site_path / template_path.stem
        if template_str_fragment in site_pth_map:
            site_pth_path = site_pth_map.pop(template_str_fragment)

        if not site_pth_path.exists():
            with site_pth_path.open("w") as site_pth_path_f:
                site_pth_path_f.write(filled_in_path)

    for site_pth in site_pth_map:
        site_pth_map[site_pth].unlink()


def add_srcdirs_to_syspath() -> None:
    """
    Add all src directories under current working directory to sys.path. If CWD is not the
    project root (containing root 'src' directory), walk up ancestry to find a directory
    containing a 'src' directory. Waking up allows for being within in the 'tests' directory
    when initiating tests against modules under 'root/src'.

    Searching for 'src' directories is NOT limited to finding the '<project root>/src' (and 'src'
    directories under that '<project root>/src' directory)! All those will be found and added,
    but also any other 'src' directory found under the <project root>/tests tree. This is desired
    since git subprojects may be under 'tests' and their 'src' directories need to be
    included.

    :return: None
    """
    root_path: Path = Path(get_project_root_dir())

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

    all_src_dirs: Generator[Path, None, None] = root_path.glob("src")
    all_test_src_dirs: Generator[Path, None, None] = root_path.glob("tests/**/src")

    tested_src: Path
    for tested_src in chain.from_iterable([all_src_dirs, all_test_src_dirs]):
        tested_src_str = str(tested_src)
        if tested_src.is_dir() and tested_src_str not in sys.path:
            sys.path.append(tested_src_str)

    diff_path_strs: Set[str] = set(prior_sys_path).symmetric_difference(set(sys.path))
    if len(diff_path_strs) > 0:
        diff_path_strs = {Path(diff_path_str).as_posix() for diff_path_str in diff_path_strs}
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
    dot_count: int = target_module.__package__.count(".") if target_module.__package__ else 0
    dots: str = dots + "".join("." for i in range(0, dot_count))
    return target_module.__package__, dots
