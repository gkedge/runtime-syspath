import atexit
import importlib
import inspect
import logging
import os
import shutil
import site
import sys
from importlib import reload
from pathlib import Path
from typing import List, Optional, Tuple

import click
import importlib_metadata
from diff_match_patch import diff_match_patch, patch_obj

from . import syspath_sleuth
from .syspath_sleuth import SysPathSleuth

PRE_SLEUTH_SUFFIX = ".pre_sleuth"
REVERSE_PATCH_SUFFIX = ".patch"

error_logger: logging.Logger = logging.getLogger(f"{__name__}.error")
error_logger.addHandler(logging.StreamHandler(sys.stderr))

sleuth_logger: logging.Logger = logging.getLogger(error_logger.parent.name)
sleuth_logger.addHandler(logging.StreamHandler(sys.stdout))


class InstallError(RuntimeError):
    pass


class UninstallError(RuntimeError):
    pass


def append_sleuth_to_customize(customize_path: Path, syspath_sleuth_path: Optional[Path] = None):
    sleuth_logger.info(
        "Appending %s to site customize: %s",
        *get_name_and_relative_path(customize_path, syspath_sleuth_path),
    )

    lines: List[str]

    if syspath_sleuth_path:
        with syspath_sleuth_path.open() as custom_syspath_sleuth:
            lines = custom_syspath_sleuth.readlines()
    else:
        lines, _ = inspect.getsourcelines(syspath_sleuth)

    with customize_path.open("r+") as customize_path_f:
        customize_path_f.writelines(lines)


def create_site_customize(customize_path: Path):
    sleuth_logger.info("Creating system site %s", customize_path.name)
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

    sleuth_logger.info(
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

    try:
        # pylint: disable=import-outside-toplevel,unused-import
        import sitecustomize

        # pylint: enable=import-outside-toplevel,unused-import

    # This is too sketch...
    #     sys.path = sys.path.get_base_list()
    #     if isinstance(sys.path, sitecustomize.SysPathSleuth):
    #         error_logger.warning("Hmmm... expected sys.path NOT to be monkey-patched.")
    #
    except (AttributeError, ModuleNotFoundError):
        # This will occur if SysPathSleuth was not installed prior. But, don't skip the
        # uninstall_sleuth() as the user messaging associated with this condition is shared.
        pass


def get_user_customize_path():
    return Path(site.getusersitepackages()) / "usercustomize.py"


def get_system_customize_path() -> Path:
    system_site: str
    for system_site in site.getsitepackages():
        if "site-packages" in system_site:
            return Path(system_site) / "sitecustomize.py"
    raise InstallError("No system site found!")


def get_customize_path() -> Tuple[Path, bool]:
    """
    When using venv, site.ENABLE_USER_SITE is False. When using virtual environments,
    the effort is to isolate the activities within one virtual environment per Python
    system from other virtual environments. Were the user site enabled within a virtual
    environment, it would affect other Python virtual environments.

    :return:
    """
    is_user_path = False
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        customize_path = get_user_customize_path()
        customize_path.parent.mkdir(parents=True, exist_ok=True)
        is_user_path = True
    else:
        customize_path = get_system_customize_path()
    return customize_path, is_user_path


def get_name_and_relative_path(
    customize_path: Path, syspath_sleuth_path: Optional[Path]
) -> Tuple[str, Path]:
    if syspath_sleuth_path:
        sleuth_name = syspath_sleuth_path.name
        sleuth_path: Path = get_relative_path(customize_path)
    else:
        sleuth_name = SysPathSleuth.__name__
        sleuth_path = SysPathSleuth.relative_path(customize_path)
    return sleuth_name, sleuth_path


def get_relative_path(path: Path) -> Path:
    sleuth_path: Path = path
    try:
        sleuth_path = path.relative_to(Path.cwd())
    except ValueError:
        pass
    return sleuth_path


def inject_sleuth(syspath_sleuth_path: Optional[Path] = None):

    customize_path, is_user_path = get_customize_path()

    if customize_path and customize_path.exists():
        name, _ = get_name_and_relative_path(customize_path, syspath_sleuth_path)
        sleuth_logger.warning(
            "Reinstalling %s in %s site...", name, "user" if is_user_path else "system"
        )
        reverse_patch_sleuth(customize_path)

    create_site_customize(customize_path)
    copy_site_customize(customize_path)
    append_sleuth_to_customize(customize_path, syspath_sleuth_path)
    create_reverse_sleuth_patch(customize_path)

    # Determine if the customize site was updated to wrap sys.path with a SysPathSleuth.
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        customize_module = importlib.import_module("usercustomize")
    else:
        customize_module = importlib.import_module("sitecustomize")
    reload(customize_module)
    class_names: Tuple[str] = tuple(
        x[0] for x in inspect.getmembers(customize_module, inspect.isclass)
    )
    if "SysPathSleuth" not in class_names or not isinstance(
        sys.path, customize_module.SysPathSleuth
    ):
        # The file loaded doesn't wrap sys.path with a SysPathSleuth
        sleuth_logger.setLevel(logging.ERROR)
        reverse_patch_sleuth(customize_path)
        _, sleuth_path = get_name_and_relative_path(customize_path, syspath_sleuth_path)
        raise InstallError(f"{sleuth_path} does not wrap sys.path with a SysPathSleuth.")


def uninstall_sleuth():
    # When using venv, site.ENABLE_USER_SITE is False. When using virtual environments,
    # the effort is to isolate the activities within one virtual environment per Python
    # system Python from other virtual environments. Were the user site enabled, it would
    # affect other Python virtual environments.
    customize_path, is_user_path = get_customize_path()

    if not customize_path.exists():
        error_logger.warning(
            "%s was not installed in %s site: %s",
            SysPathSleuth.__name__,
            "user" if is_user_path else "system",
            SysPathSleuth.relative_path(customize_path),
        )
        return

    reverse_patch_sleuth(customize_path)

    sleuth_logger.warning(
        "%s uninstalled from %s site: %s",
        SysPathSleuth.__name__,
        "user" if is_user_path else "system",
        SysPathSleuth.relative_path(customize_path),
    )


@click.command(
    help="(Un)Install SysPathSleuth into user-site or system-site to track sys.path "
    "access in real-time."
)
@click.version_option(version=importlib_metadata.version("runtime-syspath"))
@click.option("--inject/--uninstall", "-i/-u", default=False, help="default=uninstall")
@click.option(
    "--custom",
    "-c",
    type=click.Path(exists=True, resolve_path=True),
    help="path to a user's implementation of a SysPathSleuth",
)
@click.option("--verbose", "-v", is_flag=True, default=False)
def syspath_sleuth_main(inject: bool, custom: Optional[str], verbose: Optional[bool]):
    custom_path: Optional[Path] = Path(custom) if custom else None
    if verbose:
        sleuth_logger.setLevel(logging.INFO)
        for handler in sleuth_logger.handlers:
            handler.setLevel(logging.INFO)

    # pylint: disable=broad-except
    try:
        if inject:
            inject_sleuth(custom_path)

            # handler = logging.StreamHandler(sys.stdout)
            # handler.setLevel(logging.INFO)
            # sys.path.config_logger(handler, logging.INFO)
            # sys.path.append('yow')
        else:
            try:
                # pylint: disable=import-outside-toplevel,unused-import
                import sitecustomize

                # pylint: enable=import-outside-toplevel,unused-import

            # This so sketch...
            #     sys.path = sys.path.get_base_list()
            #     if isinstance(sys.path, sitecustomize.SysPathSleuth):
            #         error_logger.warning("Hmmm... expected sys.path NOT to be monkey-patched.")
            #
            except (AttributeError, ModuleNotFoundError):
                # This will occur if SysPathSleuth was not installed prior. But, don't skip the
                # uninstall_sleuth() as the user messaging associated with this condition is shared.
                pass

            uninstall_sleuth()
    except Exception as ex:
        error_logger.error("%s failed: %s", "Inject" if inject else "Uninstall", ex)


def is_install_on_import():
    return bool(
        os.getenv("SYSPATH_SLEUTH_INSTALL_ON_IMPORT") is not None
        and os.getenv("SYSPATH_SLEUTH_KILL") is None
    )


if is_install_on_import():
    # WARNING: This could be surprising since it would be rather easy to have SysPathSleuth install
    # without seeming to do much.
    error_logger.warning("Installing SysPathSleuth on import.")
    inject_sleuth()
    atexit.register(uninstall_sleuth)
