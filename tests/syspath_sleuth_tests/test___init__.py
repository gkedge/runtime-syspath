import argparse
import inspect
import logging
from pathlib import Path
import site
from typing import List

from _pytest.capture import CaptureResult
import pytest

import syspath_sleuth
from syspath_sleuth import SysPathSleuth


def test_parse_args_install():
    parser = argparse.ArgumentParser()
    arg_namespace: argparse.Namespace = syspath_sleuth.parse_syspath_sleuth_args(["-i"], parser)

    assert arg_namespace is not None and arg_namespace.install

    parser = argparse.ArgumentParser()
    arg_namespace: argparse.Namespace = syspath_sleuth.parse_syspath_sleuth_args(
        ["--install"], parser
    )

    assert arg_namespace is not None and arg_namespace.install


def test_parse_args_uninstall():
    parser = argparse.ArgumentParser()
    arg_namespace: argparse.Namespace = syspath_sleuth.parse_syspath_sleuth_args(["-u"], parser)

    assert arg_namespace is not None and arg_namespace.uninstall

    parser = argparse.ArgumentParser()
    arg_namespace: argparse.Namespace = syspath_sleuth.parse_syspath_sleuth_args(
        ["--uninstall"], parser
    )

    assert arg_namespace is not None and arg_namespace.uninstall


def test_parse_args_help(capsys):
    try:
        syspath_sleuth.parse_syspath_sleuth_args(["-h"], argparse.ArgumentParser())

        pytest.fail("'-h' should exit.")
    except SystemExit:
        result: CaptureResult = capsys.readouterr()
        assert "usage:" in result.out and "(-i | -u)" in result.out
        assert (
            f"-i, --install    Install {SysPathSleuth.__name__} to user-site if available, else"
            in result.out
        )
        assert (
            f"-u, --uninstall  Uninstall {SysPathSleuth.__name__} from both user-site and/or "
            "system-" in result.out
        )


def test_parse_args_bad(capsys):
    try:
        argparse.Namespace = syspath_sleuth.parse_syspath_sleuth_args(
            None, argparse.ArgumentParser()
        )
        pytest.fail("At lease one arg is required.")
    except SystemExit:
        result: CaptureResult = capsys.readouterr()
        assert "usage:" in result.err and "(-i | -u)" in result.err
        assert "error: one of the arguments -i/--install -u/--uninstall is required" in result.err

    try:
        syspath_sleuth.parse_syspath_sleuth_args(["-i", "-u"], argparse.ArgumentParser())
        pytest.fail("'-i' and '-u' are mutually exclusive.")
    except SystemExit:
        result: CaptureResult = capsys.readouterr()
        assert "usage:" in result.err and "(-i | -u)" in result.err
        assert (
            "error: argument -u/--uninstall: not allowed with argument -i/--install" in result.err
        )


def test_get_system_customize_path():
    customize_path: Path = syspath_sleuth.get_system_customize_path()
    assert (
        customize_path
        and customize_path.name == "sitecustomize.py"
        and customize_path.parent.stem == "site-packages"
        and "python" in customize_path.parent.parent.stem
    )


def test_create_site_customize(request, caplog):
    test_path = Path("yow.yowsa")

    def fin():
        if test_path.exists():
            test_path.unlink()

    if test_path.exists():
        test_path.unlink()

    request.addfinalizer(finalizer=fin)

    syspath_sleuth.create_site_customize(test_path)

    record: logging.LogRecord
    for record in caplog.get_records("call"):
        if "Creating system site: yow.yowsa" in record.message:
            assert record.levelname == "INFO"
            break

    assert test_path.exists()


def test_copy_site_customize(request):
    test_path = Path("yow")
    copied_file_path = test_path.with_suffix(syspath_sleuth.PRE_SLEUTH_SUFFIX)

    def fin():
        if test_path.exists():
            test_path.unlink()
        if copied_file_path.exists():
            copied_file_path.unlink()

    request.addfinalizer(finalizer=fin)
    if test_path.exists():
        test_path.unlink()
    if copied_file_path.exists():
        copied_file_path.unlink()

    syspath_sleuth.create_site_customize(test_path)
    syspath_sleuth.copy_site_customize(test_path)

    assert copied_file_path.exists()


def test_append_sleuth_to_customize(request, caplog):
    caplog.set_level(logging.INFO)
    customize_path = Path("yow")

    def fin():
        if customize_path.exists():
            customize_path.unlink()

    request.addfinalizer(finalizer=fin)
    if customize_path.exists():
        customize_path.unlink()

    syspath_sleuth.create_site_customize(customize_path)
    syspath_sleuth.append_sleuth_to_customize(customize_path)
    record: logging.LogRecord
    for record in caplog.get_records("call"):
        if f"Appending {SysPathSleuth.__name__} to site customize: yow" in record.message:
            assert record.levelname == "INFO"
            break
    else:
        pytest.fail("Did not find expected log record.")

    assert customize_path.exists()
    src_lines: List[str]
    src_lines, _ = inspect.getsourcelines(syspath_sleuth.syspath_sleuth)

    with customize_path.open() as site_customize_path_f:
        site_customize_lines: List[str] = site_customize_path_f.readlines()

    assert src_lines == site_customize_lines


def test_create_reverse_sleuth_patch(request):
    customize_path = Path("yow")
    copied_customize_path = customize_path.with_suffix(syspath_sleuth.PRE_SLEUTH_SUFFIX)
    reverse_patch_path = customize_path.with_suffix(syspath_sleuth.REVERSE_PATCH_SUFFIX)

    def fin():
        if customize_path.exists():
            customize_path.unlink()
        if copied_customize_path.exists():
            copied_customize_path.unlink()
        if reverse_patch_path.exists():
            reverse_patch_path.unlink()

    request.addfinalizer(finalizer=fin)
    if customize_path.exists():
        customize_path.unlink()
    if copied_customize_path.exists():
        copied_customize_path.unlink()
    if reverse_patch_path.exists():
        reverse_patch_path.unlink()

    syspath_sleuth.create_site_customize(customize_path)
    assert customize_path.exists()

    syspath_sleuth.copy_site_customize(customize_path)
    copied_customize_path.exists()

    syspath_sleuth.append_sleuth_to_customize(customize_path)
    assert customize_path.exists() and customize_path.stat().st_size > 0

    syspath_sleuth.create_reverse_sleuth_patch(customize_path)
    assert not copied_customize_path.exists()
    assert reverse_patch_path.exists()


def test_reverse_patch_sleuth(request, caplog):
    caplog.set_level(logging.INFO)
    customize_path = Path("yow")
    copied_customize_path = customize_path.with_suffix(syspath_sleuth.PRE_SLEUTH_SUFFIX)
    reverse_patch_path = customize_path.with_suffix(syspath_sleuth.REVERSE_PATCH_SUFFIX)

    def fin():
        if customize_path.exists():
            customize_path.unlink()
        if copied_customize_path.exists():
            copied_customize_path.unlink()
        if reverse_patch_path.exists():
            reverse_patch_path.unlink()

    request.addfinalizer(finalizer=fin)
    if customize_path.exists():
        customize_path.unlink()
    if copied_customize_path.exists():
        copied_customize_path.unlink()
    if reverse_patch_path.exists():
        reverse_patch_path.unlink()

    syspath_sleuth.create_site_customize(customize_path)
    assert customize_path.exists()

    syspath_sleuth.copy_site_customize(customize_path)
    copied_customize_path.exists()

    syspath_sleuth.append_sleuth_to_customize(customize_path)
    assert customize_path.exists() and customize_path.stat().st_size > 0

    syspath_sleuth.create_reverse_sleuth_patch(customize_path)
    assert not copied_customize_path.exists()
    assert reverse_patch_path.exists()

    syspath_sleuth.reverse_patch_sleuth(customize_path)

    assert not reverse_patch_path.exists()
    assert customize_path.exists() and customize_path.stat().st_size == 0

    record: logging.LogRecord
    for record in caplog.get_records("call"):
        if f"Removing {SysPathSleuth.__name__} from site customize: yow" in record.message:
            assert record.levelname == "INFO"
            break
    else:
        pytest.fail("Did not find expected log record.")


def test_inject_sleuth(request, caplog):
    caplog.set_level(logging.INFO)
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        customize_path = syspath_sleuth.get_user_customize_path()
    else:
        customize_path = syspath_sleuth.get_system_customize_path()
    copied_customize_path = customize_path.with_suffix(syspath_sleuth.PRE_SLEUTH_SUFFIX)
    reverse_patch_path = customize_path.with_suffix(syspath_sleuth.REVERSE_PATCH_SUFFIX)

    if customize_path.exists():
        customize_path.unlink()
    if reverse_patch_path.exists():
        reverse_patch_path.unlink()

    def fin():
        if customize_path.exists():
            customize_path.unlink()
        if reverse_patch_path.exists():
            reverse_patch_path.unlink()

    request.addfinalizer(finalizer=fin)

    syspath_sleuth.inject_sleuth()
    assert customize_path.exists() and customize_path.stat().st_size != 0
    assert reverse_patch_path.exists() and reverse_patch_path.stat().st_size != 0
    assert not copied_customize_path.exists()
    with customize_path.open() as customize_f:
        assert f"class {SysPathSleuth.__name__}" in customize_f.read()

    creating_message = "Creating system site sitecustomize.py"
    append_message = f"Appending {SysPathSleuth.__name__} to site customize: {customize_path}"
    record: logging.LogRecord
    for record, message in zip(caplog.get_records("call"), [creating_message, append_message]):
        assert record.getMessage() == message, "Did not find expected log record message."
        assert record.levelname == "INFO", "Did not find expected log record level."

    caplog.clear()

    # Inject a second time; should remove existing and re-append SysPathSleuth
    syspath_sleuth.inject_sleuth()
    assert customize_path.exists() and customize_path.stat().st_size != 0
    assert reverse_patch_path.exists() and reverse_patch_path.stat().st_size != 0
    assert not copied_customize_path.exists()
    with customize_path.open() as customize_f:
        assert f"class {SysPathSleuth.__name__}" in customize_f.read()

    removing_message = f"Removing {SysPathSleuth.__name__} from site customize: {customize_path}"
    append_message = f"Appending {SysPathSleuth.__name__} to site customize: {customize_path}"
    record: logging.LogRecord
    for record, message in zip(caplog.records, [removing_message, append_message]):
        assert record.getMessage() == message, "Did not find expected log record message."
        assert record.levelname == "INFO", "Did not find expected log record level."


def test_uninstall_sleuth(request, caplog):
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        customize_path = syspath_sleuth.get_user_customize_path()
    else:
        customize_path = syspath_sleuth.get_system_customize_path()
    reverse_patch_path = customize_path.with_suffix(syspath_sleuth.REVERSE_PATCH_SUFFIX)
    if customize_path.exists():
        customize_path.unlink()

    def fin():
        if customize_path.exists():
            customize_path.unlink()

    request.addfinalizer(finalizer=fin)

    syspath_sleuth.inject_sleuth()

    caplog.set_level(logging.INFO)
    syspath_sleuth.uninstall_sleuth()
    assert customize_path.exists() and customize_path.stat().st_size == 0
    assert not reverse_patch_path.exists()

    removing_message = f"Removing {SysPathSleuth.__name__} from site customize: {customize_path}"
    record: logging.LogRecord
    for record, message in zip(caplog.get_records("call"), [removing_message]):
        assert record.getMessage() == message, "Did not find expected log record message."
        assert record.levelname == "INFO", "Did not find expected log record level."

    caplog.clear()

    # Uninstall a second time; should be a noop
    syspath_sleuth.uninstall_sleuth()
    assert customize_path.exists() and customize_path.stat().st_size == 0
    assert not reverse_patch_path.exists()

    assert len(caplog.records) == 0


def test_main(request, caplog):

    syspath_sleuth.main(["-i"])
    test_inject_sleuth(request, caplog=caplog)
    syspath_sleuth.main(["-u"])
    test_uninstall_sleuth(request, caplog=caplog)
