import argparse
import inspect
import logging
import os
from pathlib import Path
from typing import List

from _pytest.capture import CaptureResult
from diff_match_patch import diff_match_patch
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
    syspath_sleuth.copy_site_customize(customize_path)
    syspath_sleuth.append_sleuth_to_customize(customize_path)
    syspath_sleuth.create_reverse_sleuth_patch(customize_path)

    assert reverse_patch_path.exists()

    with reverse_patch_path.open() as customize_patch_f:
        patch = customize_patch_f.read()

    with customize_path.open() as customize_patch_f:
        customize = customize_patch_f.read()

    dmp = diff_match_patch()
    patches: List[str] = dmp.patch_fromText(patch)
    patched_customize: str
    patch_results: List[bool]
    patched_customize, patch_results = dmp.patch_apply(patches, customize)

    for patch_result in patch_results:
        assert patch_result

    assert not patched_customize

    with customize_path.open("w") as customize_patch_f:
        customize_patch_f.write(patched_customize)

    assert reverse_patch_path.exists()


def test_reverse_existing_sleuth(request, caplog):
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

    syspath_sleuth.reverse_existing_sleuth(customize_path)

    assert not reverse_patch_path.exists()
    assert customize_path.exists() and customize_path.stat().st_size == 0
    record: logging.LogRecord
    for record in caplog.get_records("call"):
        if f"Removing {SysPathSleuth.__name__} from site customize: yow" in record.message:
            assert record.levelname == "INFO"
            break
    else:
        pytest.fail("Did not find expected log record.")


def test_main(capsys):
    syspath_sleuth.main(["-u"])
    results: CaptureResult = capsys.readouterr()
    # assert results.out == "{'install': False, 'uninstall': True}\n"
