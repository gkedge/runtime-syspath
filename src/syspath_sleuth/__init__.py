import argparse
import importlib
import inspect
import logging
import shutil
import site
import sys
from importlib import reload
from pathlib import Path
from typing import List, Optional, Sequence

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
            description=f"(Un)Install {SysPathSleuth.__name__} into user-site or system-site "
            f"to track sys.path access in real-time."
        )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-i",
        "--install",
        action="store_true",
        help=f"Install {SysPathSleuth.__name__} to user-site if available, else system-site",
    )
    group.add_argument(
        "-u",
        "--uninstall",
        action="store_true",
        help=f"Uninstall {SysPathSleuth.__name__} from both user-site and/or system-site",
    )
    return parser.parse_args(args)


def append_sleuth_to_customize(customize_path):
    logger.info(
        "Appending %s to site customize: %s",
        SysPathSleuth.__name__,
        SysPathSleuth.relative_path(customize_path),
    )
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


def reverse_patch_sleuth(customize_path):
    reverse_patch_path = customize_path.with_suffix(REVERSE_PATCH_SUFFIX)
    if not reverse_patch_path.exists():
        return

    logger.info(
        "Removing %s from site customize: %s",
        SysPathSleuth.__name__,
        SysPathSleuth.relative_path(customize_path),
    )
    with reverse_patch_path.open() as customize_patch_f:
        patch = customize_patch_f.read()

        dmp = diff_match_patch()
        patches: List[str] = dmp.patch_fromText(patch)

    patched_customize: str
    patch_results: List[bool]
    with customize_path.open("r") as customize_patch_f:
        customize = customize_patch_f.read()
        patched_customize, patch_results = dmp.patch_apply(patches, customize)
        save_patched = bool(patched_customize)
        for patch_result in patch_results:
            if not patch_result:
                raise UninstallError(
                    f"Reverse patch failed; patch file: "
                    f"{reverse_patch_path}.\n"
                    f"Hand edit removal of {SysPathSleuth.__name__}"
                )
        if save_patched:
            with customize_path.open("w") as customize_patch_f:
                customize_patch_f.seek(0)
                customize_patch_f.write(patched_customize)

    reverse_patch_path.unlink()
    if not save_patched:
        customize_path.unlink()


def get_user_customize_path():
    return Path(site.getusersitepackages()) / "usercustomize.py"


def get_system_customize_path() -> Path:
    system_site: str
    for system_site in site.getsitepackages():
        if "site-packages" in system_site:
            return Path(system_site) / "sitecustomize.py"
    raise InstallError("No system site found!")


def inject_sleuth():
    # When using venv, site.ENABLE_USER_SITE is False. When using virtual environments,
    # the effort is to isolate the activities within one virtual environment per Python
    # system Python from other virtual environments. Were the user site enabled, it would
    # affect other Python virtual environments.
    user_path = False
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        customize_path = get_user_customize_path()
        customize_path.parent.mkdir(parents=True, exist_ok=True)
        user_path = True
    else:
        customize_path = get_system_customize_path()

    if customize_path and customize_path.exists():
        logger.warning(
            "Reinstalling %s in %s site...",
            SysPathSleuth.__name__,
            "user" if user_path else "system",
        )
        reverse_patch_sleuth(customize_path)

    create_site_customize(customize_path)
    copy_site_customize(customize_path)
    append_sleuth_to_customize(customize_path)
    create_reverse_sleuth_patch(customize_path)
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        reload(importlib.import_module("usercustomize"))
    else:
        reload(importlib.import_module("sitecustomize"))


def uninstall_sleuth():
    # When using venv, site.ENABLE_USER_SITE is False. When using virtual environments,
    # the effort is to isolate the activities within one virtual environment per Python
    # system Python from other virtual environments. Were the user site enabled, it would
    # affect other Python virtual environments.
    user_path = False
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        user_path = True
        customize_path = get_user_customize_path()
    else:
        customize_path = get_system_customize_path()

    if not customize_path.exists():
        logger.warning(
            "%s was not installed in %s site: %s",
            SysPathSleuth.__name__,
            "user" if user_path else "system",
            SysPathSleuth.relative_path(customize_path),
        )
        return

    reverse_patch_sleuth(customize_path)

    logger.warning(
        "%s uninstalled from %s site: %s",
        SysPathSleuth.__name__,
        "user" if user_path else "system",
        SysPathSleuth.relative_path(customize_path),
    )


def syspath_sleuth_main(args: Optional[Sequence[str]] = None):
    args_namespace: argparse.Namespace = parse_syspath_sleuth_args(args)

    if args_namespace.install:
        inject_sleuth()

        # pylint: disable=import-outside-toplevel
        import sitecustomize

        # pylint: enable=import-outside-toplevel

        if not isinstance(sys.path, sitecustomize.SysPathSleuth):
            print("Hmmm... expected sys.path to be monkey-patched.")
        # handler = logging.StreamHandler(sys.stdout)
        # handler.setLevel(logging.INFO)
        # sys.path.config_logger(handler, logging.INFO)
        # sys.path.append('yow')
    elif args_namespace.uninstall:
        try:
            # pylint: disable=import-outside-toplevel
            import sitecustomize

            # pylint: enable=import-outside-toplevel

            # Removing the monkey-patch seems rife with pending disaster if used during running
            # execution and not about to exit (like this installer is about to), and in that case,
            # is it really worth it(?). But, it seems to work, doing it in your own
            # implementation, YMMV.
            sys.path = sys.path.get_base_list()
            if isinstance(sys.path, sitecustomize.SysPathSleuth):
                print("Hmmm... expected sys.path NOT to be monkey-patched.")

        except AttributeError:
            # This will occur if SysPathSleuth was not installed prior. But, don't skip the
            # uninstall_sleuth() as the user messaging associated with this condition is shared.
            pass

        uninstall_sleuth()

    else:
        raise InstallError("Not install or uninstall? Confused")
