import argparse
import logging

from pathlib import Path
from pprint import pprint
import site
from typing import Optional, Sequence

from .syspath_sleuth import SysPathSleuth

logger: logging.Logger = logging.getLogger(__name__)


class InstallError(RuntimeError):
    pass


def parse_syspath_sleuth_args(args: Optional[Sequence[str]] = None, parser: argparse.ArgumentParser = None):
    """Parse command line arguments, return argparse namespace."""
    if not parser:
        parser = argparse.ArgumentParser(
        description="(Un)Install SysPathSleuth into user-site or system-site to track sys.path "
                    "access in real-time."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-i', '--install', action='store_true',
        help="Install SysPathSleuth to user-site if available, else system-site",
    )
    group.add_argument(
        '-u', '--uninstall', action='store_true',
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
    sleuth_message = (
        f"Appending SysPathSleuth to user site customize: {user_customize_path}"
    )
    logger.info(sleuth_message)


def append_sleuth_to_customize(system_customize_path):
    sleuth_message = (
        f"Appending SysPathSleuth to system site customize: {system_customize_path}"
    )
    logger.info(sleuth_message)


def create_site_customize(system_customize_path: Path) -> bool:
    return False


def inject_sleuth_into_system_site():
    system_customize_path = Path(site.getsitepackages()[0]) / "sitecustomize.py"
    if system_customize_path.exists():
        append_sleuth_to_customize(system_customize_path)
    elif create_site_customize(system_customize_path):
        pass
    else:
        raise InstallError("Unable to install SysPathSleuth to system site.")


def remove_sleuth_into_user_site():
    pass


def remove_sleuth_into_system_site():
    pass


def main(args: Optional[Sequence[str]] = None):
    args_namespace: argparse.Namespace = parse_syspath_sleuth_args(args)

    if args_namespace.install:
        if site.ENABLE_USER_SITE and site.check_enableusersite():
            inject_sleuth_into_user_site()
        else:
            inject_sleuth_into_system_site()
    elif args_namespace.uninstall:
        if site.ENABLE_USER_SITE and site.check_enableusersite():
            remove_sleuth_into_user_site()
        remove_sleuth_into_system_site()
    else:
        raise InstallError("Not install or uninstall? Confused")

