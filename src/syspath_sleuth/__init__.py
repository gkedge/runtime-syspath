import argparse
import inspect
import logging
from pathlib import Path
import shutil
import site
from typing import Optional, Sequence, List

from diff_match_patch import diff_match_patch, patch_obj

from . import syspath_sleuth
from .syspath_sleuth import SysPathSleuth

PRE_SLEUTH_SUFFIX = ".pre_sleuth"
REVERSE_PATCH_SUFFIX = ".patch"

logger: logging.Logger = logging.getLogger(__name__)


class InstallError(RuntimeError):
    pass


class UninstallError(RuntimeError):
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


def append_sleuth_to_customize(customize_path):
    logger.info("Appending %s to site customize: %s", SysPathSleuth.__name__, customize_path)
    lines: List[str]
    lines, _ = inspect.getsourcelines(syspath_sleuth)

    with customize_path.open("r+") as customize_path_f:
        customize_path_f.writelines(lines)


def create_site_customize(customize_path: Path):
    logger.info("Creating system site %s", customize_path.name)
    customize_path.touch()


def copy_site_customize(customize_path: Path):
    shutil.copy(customize_path, customize_path.with_suffix(PRE_SLEUTH_SUFFIX))


def create_reverse_sleuth_patch(customize_path):
    pre_sleuth_customize_path = customize_path.with_suffix(PRE_SLEUTH_SUFFIX)
    if customize_path.exists and pre_sleuth_customize_path.exists:
        customize: str
        with customize_path.open() as customize_f:
            customize = customize_f.read()

        pre_sleuth_site_customize: str
        with pre_sleuth_customize_path.open() as pre_sleuth_customize_f:
            pre_sleuth_site_customize = pre_sleuth_customize_f.read()

        dmp = diff_match_patch()
        diffs: List[patch_obj] = dmp.diff_main(
            customize, pre_sleuth_site_customize, checklines=False
        )
        patches = dmp.patch_make(diffs)
        customize_reverse_patch: Path = customize_path.with_suffix(REVERSE_PATCH_SUFFIX)
        reverse_patch: str = dmp.patch_toText(patches)

        with customize_reverse_patch.open("x") as customize_reverse_patch_f:
            customize_reverse_patch_f.writelines(reverse_patch)

        pre_sleuth_customize_path.unlink()


def reverse_existing_sleuth(customize_path):
    logger.info("Removing %s from site customize: %s", SysPathSleuth.__name__, customize_path)
    reverse_patch_path = customize_path.with_suffix(REVERSE_PATCH_SUFFIX)
    if reverse_patch_path.exists():
        with reverse_patch_path.open() as customize_patch_f:
            patch = customize_patch_f.read()

            dmp = diff_match_patch()
            patches: List[str] = dmp.patch_fromText(patch)

        patched_customize: str
        patch_results: List[bool]
        with customize_path.open("r") as customize_patch_f:
            customize = customize_patch_f.read()
            patched_customize, patch_results = dmp.patch_apply(patches, customize)

            for patch_result in patch_results:
                if not patch_result:
                    raise UninstallError(
                        f"Reverse patch failed; patch file: "
                        f"{reverse_patch_path}.\n"
                        f"Hand edit removal of {SysPathSleuth.__name__}"
                    )

            with customize_path.open("w") as customize_patch_f:
                customize_patch_f.seek(0)
                customize_patch_f.write(patched_customize)

        reverse_patch_path.unlink()


def get_user_customize_path():
    return Path(site.getusersitepackages()) / "usercustomize.py"


def get_system_customize_path() -> Path:
    system_site: str
    for system_site in site.getsitepackages():
        if "site-packages" in system_site:
            return Path(system_site) / "sitecustomize.py"
    raise InstallError("No system site found!")


def remove_sleuth_into_user_site():
    pass


def remove_sleuth_into_system_site():
    pass


def inject_sleuth():
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        customize_path = get_user_customize_path()
        customize_path.parent.mkdir(parents=True)
    else:
        customize_path = get_system_customize_path()

    if customize_path and not customize_path.exists():
        create_site_customize(customize_path)
    else:
        reverse_existing_sleuth(customize_path)
    copy_site_customize(customize_path)
    append_sleuth_to_customize(customize_path)
    create_reverse_sleuth_patch(customize_path)


def uninstall_sleuth():
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        remove_sleuth_into_user_site()
    remove_sleuth_into_system_site()


def main(args: Optional[Sequence[str]] = None):
    args_namespace: argparse.Namespace = parse_syspath_sleuth_args(args)

    if args_namespace.install:
        inject_sleuth()
    elif args_namespace.uninstall:
        uninstall_sleuth()
    else:
        raise InstallError("Not install or uninstall? Confused")
