import argparse
import difflib
import inspect
import logging
from pathlib import Path
import shutil
import site
from typing import Optional, Sequence, List, Iterator

from . import syspath_sleuth

logger: logging.Logger = logging.getLogger(__name__)


class InstallError(RuntimeError):
    pass


def parse_syspath_sleuth_args(
        args: Optional[Sequence[str]] = None, parser: argparse.ArgumentParser = None
):
    """Parse command line arguments, return argparse namespace."""
    if not parser:
        parser = argparse.ArgumentParser(
            description="(Un)Install SysPathSleuth into user-site or system-site to track sys.path "
                        "access in real-time."
        )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-i",
        "--install",
        action="store_true",
        help="Install SysPathSleuth to user-site if available, else system-site",
    )
    group.add_argument(
        "-u",
        "--uninstall",
        action="store_true",
        help="Uninstall SysPathSleuth from both user-site and/or system-site",
    )
    return parser.parse_args(args)


def create_user_site_customize(user_customize_path):
    pass


def inject_sleuth_into_user_site():
    user_customize_path = Path(site.getusersitepackages()) / "usercustomize.py"
    if user_customize_path.exists():
        append_sleuth_to_usercustomize(user_customize_path)
    elif create_user_site_customize(user_customize_path):
        pass
    else:
        raise InstallError("Unable to install SysPathSleuth to user site.")


def append_sleuth_to_usercustomize(user_customize_path: Path):
    sleuth_message = f"Appending SysPathSleuth to user site customize: {user_customize_path}"
    logger.info(sleuth_message)


def append_sleuth_to_customize(system_customize_path):
    logger.info("Appending SysPathSleuth to system site customize: %s", system_customize_path)
    lines: List[str]
    lines, _ = inspect.getsourcelines(syspath_sleuth)

    with system_customize_path.open('r+') as system_customize_path_f:
        system_customize_path_f.writelines(lines)


def create_site_customize(system_customize_path: Path):
    logger.info(f"Creating system site {system_customize_path.name}")
    system_customize_path.touch()


def copy_site_customize(system_customize_path: Path):
    shutil.copy(system_customize_path, system_customize_path.name + '.pre_sleuth')


def create_reverse_sleuth_patch(system_customize_path):
    pre_sleuth_site_customize_path = Path(system_customize_path.stem + '.pre_sleuth')
    if system_customize_path.exists and pre_sleuth_site_customize_path.exists:
        system_customize_lines: List[str]
        with system_customize_path.open() as system_customize_f:
            system_customize_lines = system_customize_f.readlines()

        pre_sleuth_site_customize_lines: List[str]
        with pre_sleuth_site_customize_path.open() as pre_sleuth_site_customize_f:
            pre_sleuth_site_customize_lines = pre_sleuth_site_customize_f.readlines()

        unified_diff_lines: Iterator[str] = \
            difflib.unified_diff(system_customize_lines, pre_sleuth_site_customize_lines)
        site_customize_reverse_patch: Path = \
            system_customize_path.parent / system_customize_path.stem + '_reverse_sleuth.patch'

        with site_customize_reverse_patch.open() as site_customize_reverse_patch_f:
            site_customize_reverse_patch_f.writelines(unified_diff_lines)

        pre_sleuth_site_customize_path.unlink()


def reverse_existing_sleuth(system_customize_path):
    reverse_patch_path = system_customize_path.parent / system_customize_path.stem + \
                         '_reverse_sleuth.patch'
    if reverse_patch_path.exists():
        pass  # replace with application of reverse patch on system_customize_path
        reverse_patch_path.unlink()


def inject_sleuth_into_system_site():
    system_customize_path: Path = get_system_customize_path()

    if system_customize_path and not system_customize_path.exists():
        create_site_customize(system_customize_path)
    else:
        reverse_existing_sleuth(system_customize_path)
    copy_site_customize(system_customize_path)
    append_sleuth_to_customize(system_customize_path)
    create_reverse_sleuth_patch(system_customize_path)


def get_system_customize_path() -> Path:
    system_site: str
    for system_site in site.getsitepackages():
        if 'site-packages' in system_site:
            return Path(system_site) / "sitecustomize.py"
    raise InstallError("No system site found!")


def remove_sleuth_into_user_site():
    pass


def remove_sleuth_into_system_site():
    pass


def main(args: Optional[Sequence[str]] = None):
    args_namespace: argparse.Namespace = parse_syspath_sleuth_args(args)

    if args_namespace.install:
        inject_sleuth()
    elif args_namespace.uninstall:
        uninstall_sleuth()
    else:
        raise InstallError("Not install or uninstall? Confused")


def uninstall_sleuth():
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        remove_sleuth_into_user_site()
    remove_sleuth_into_system_site()


def inject_sleuth():
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        inject_sleuth_into_user_site()
    else:
        inject_sleuth_into_system_site()
