""" syspath_utils module. """
import os
import re
import sys
from itertools import chain
from pathlib import Path, PurePath
from string import Template
from types import ModuleType
from typing import Dict, List, Optional, Pattern, Set, Tuple, Union

from .syspath_path_utils import get_project_root_dir
from .syspath_sleuth import get_customize_path

_STD_SYSPATH_FILTER: Union[None, Pattern] = None

PATH_TO_PROJECT_PLACEHOLDER = "path_to_project"


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
    path_filter: Pattern = None,
    no_filtering: bool = False,
    sort: bool = False,
    unique: bool = False,
) -> List[str]:
    """
    Filter and sort the sys.path for only paths of interest.
    :param path_filter: a pattern that the caller can provide in addition to the std_syspath_filter
    :param no_filtering: allow user to not filter at all
    :param sort: allow caller to sort the filtered (if filtering) sys.path
    :param unique: allow caller to only return unique members of sys.path
    :return: sys.path with filtering and sorting applied
    """
    paths: List[str] = sys.path
    if not no_filtering:
        path: str
        if _STD_SYSPATH_FILTER:
            paths = [path for path in paths if not re.search(_STD_SYSPATH_FILTER, path)]
        if path_filter:
            paths = [path for path in paths if not re.search(path_filter, path)]

    if sort:
        paths = sorted(paths, reverse=True)

    if unique:
        unique_paths: List[str] = []
        for path in paths:
            if path not in unique_paths:
                unique_paths.append(path)

        paths = unique_paths

    return paths


def print_syspath(
    path_filter: Pattern = None, no_filtering: bool = False, sort: bool = True, unique: bool = False
) -> None:
    """
    Filter and sort the sys.path for only paths of interest.
    :param path_filter: a pattern that the caller can provide in addition to the std_syspath_filter
    :param no_filtering: caller user to not filter at all
    :param sort: allow caller to sort the filtered (if filtering) sys.path
    :param unique: allow caller to only return unique members of sys.path
    :return: None
    """
    paths: List[str] = filtered_sorted_syspath(path_filter, no_filtering, sort, unique)
    print(f"\nsys.path({len(paths)} paths):")
    path: str
    for path in paths:
        print(f"\t{path}")


def persist_syspath(
    user_provided_project_dir: Path = None,
    force_pth_dir_creation: bool = False,
    path_filter: Pattern = None,
) -> None:
    """
    Persist a set of ordered [000-999]*.pth.template files that represent each
    project-related entry in the sys.path. The files are persisted into the
    /pathto/projectroot/pths directory. If caller did not supply the /pathto/projectroot via
    'user_provided_project_dir', attempt to determine that.

    :param user_provided_project_dir: root of project using persist_syspath()
    :param force_pth_dir_creation: for directory creation
    :param path_filter: a pattern that the user can provide in addition to the std_syspath_filter
    :return: None
    """
    project_dir: PurePath = (
        user_provided_project_dir if user_provided_project_dir else get_project_root_dir()
    )

    template_dir: Path = Path(project_dir / "pths")

    if not template_dir.exists():
        create = force_pth_dir_creation or input(
            f"Create {template_dir}? [y,n] "
        ).strip().lower().startswith("y")
        if create:
            template_dir.mkdir(mode=0o766)

    sys_paths: List[str] = filtered_sorted_syspath(path_filter, unique=True)
    for index, sys_path_str in enumerate(sys_paths):
        if not sys_path_str.startswith(os.fspath(project_dir)):
            continue
        pth_path = Path(sys_path_str)
        relative_pth: PurePath = pth_path.relative_to(project_dir)
        # A project's root directory is rarely added to sys.path by a targeted application. It is
        # more likely that it was added by python itself when executing a module, e.g.:
        # python -m pytest ... or even when the Pycharm debugger is used. Skipping persisting
        # project_dir in sys.path
        if relative_pth == project_dir:
            continue
        template_path = Path(
            template_dir,
            f"{index:03d}_{project_dir.stem}_"
            f"{os.fspath(relative_pth).replace(os.sep, '_')}.pth.template",
        )

        if template_path.exists():
            continue

        with template_path.open("x") as template_path_f:
            # Write template that can be converted to wherever a project's clones are
            # rooted using inject_project_pths_to_site()
            relative_pth = (
                os.sep + os.fspath(relative_pth) if relative_pth != Path("root") else Path("")
            )
            template_path_f.write(f"${{{PATH_TO_PROJECT_PLACEHOLDER}}}{relative_pth}\n")

    dedup_pth_templates(template_dir)


def inject_project_pths_to_site(user_provided_project_dir: PurePath = None) -> None:
    """
    Iterate through all templates in /pathto/projectroot/pths converting the templates to
    the paths rooted to the current /pathto/projectroot. If caller did not supply the
    /pathto/projectroot via 'user_provided_project_dir', attempt to determine that.

    :param user_provided_project_dir: root of project using inject_project_pths_to_site()
    """
    project_dir: Path = (
        Path(user_provided_project_dir)
        if user_provided_project_dir
        else Path(get_project_root_dir())
    )

    clear_site_pths(project_dir.stem)

    template_dir: Path = Path(project_dir / "pths")
    if not template_dir.exists():
        print(f"No pth templates found within {os.fspath(template_dir)}")
        return

    site_path = get_customize_path()[0].parent
    pth_templates = get_pth_templates(template_dir)
    for template_path in pth_templates:
        site_pth_path: Path = site_path / template_path.stem
        with site_pth_path.open("w") as site_pth_path_f:
            site_pth_path_f.write(pth_templates[template_path])


def clear_site_pths(project_name: str) -> None:
    site_path = get_customize_path()[0].parent
    project_site_pth: Path
    for project_site_pth in site_path.glob(f"[0-9][0-9][0-9]_{project_name}_*.pth"):
        project_site_pth.unlink()


def dedup_pth_templates(template_dir) -> None:
    """
    get_pth_templates dedup's for us; just making it obvious that the return value has no value.
    :param template_dir:
    """
    get_pth_templates(template_dir)


def get_pth_templates(template_dir: Path) -> Dict[Path, str]:
    """
    For each template in template_dir, fill in template with 'project_name' and clean up any
    templates that would represent the same path being added to sys.path.

    :param template_dir:
    :return: dictionary mapping template Path to the filled-in string
    """
    substitution_map: Dict[str, str] = {PATH_TO_PROJECT_PLACEHOLDER: os.fspath(template_dir.parent)}
    pth_templates: Dict[Path, str] = {}
    filled_in_path_to_file_map: Dict[str, str] = {}
    templates_paths: List[Path] = list(template_dir.glob("*.pth.template"))
    templates_paths.sort()
    template_path: Path
    for template_path in templates_paths:
        with template_path.open() as template_f:
            template_str = template_f.read().strip()

        filled_in_path = Template(template_str).substitute(substitution_map)
        if filled_in_path in filled_in_path_to_file_map:
            # There are duplicate files (ordered differently) that contain the same path to be
            # added to sys.path.  The first one wins, all other template files having the same
            # paths for addition to sys.path are deleted.
            print(
                f"{template_path.name}'s {filled_in_path} already represented with "
                f"{filled_in_path_to_file_map[filled_in_path]}.\n\tDeleting {template_path.name}"
            )
            template_path.unlink()
            continue

        filled_in_path_to_file_map[filled_in_path] = template_path.name

        pth_templates[template_path] = filled_in_path

    return pth_templates


def add_srcdirs_to_syspath(user_provided_project_dir: PurePath = None) -> None:
    """
    Add all src directories under current working directory to sys.path. If caller did not supply
    the /pathto/projectroot via 'user_provided_project_dir', attempt to
    determine that, walk up ancestry to find a directory containing a 'src' directory. Waking up
    allows for being within in the 'tests' directory when initiating tests against modules under
    'root/src'.

    Searching for 'src' directories is NOT limited to finding the '<project root>/src' (and 'src'
    directories under that '<project root>/src' directory)! All those will be found and added,
    but also any other 'src' directory found under the <project root>/tests tree. This is desired
    since git subprojects may be under 'tests' and their 'src' directories need to be
    included.

    :param user_provided_project_dir: root of project using inject_project_pths_to_site()

    :return: None
    """
    project_dir: Path = (
        Path(user_provided_project_dir)
        if user_provided_project_dir
        else Path(get_project_root_dir())
    )

    prior_sys_path = sys.path.copy()

    src: Path
    for src in chain.from_iterable([project_dir.glob("src"), project_dir.glob("tests/**/src")]):
        tested_src_str = str(src)
        if src.is_dir() and tested_src_str not in sys.path:
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
