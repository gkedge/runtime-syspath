import argparse
import inspect
import logging
from pathlib import Path
from typing import List

from _pytest.capture import CaptureResult
import pytest

import syspath_sleuth


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
                "-i, --install    Install SysPathSleuth to user-site if available, else" in
                result.out
        )
        assert (
                "-u, --uninstall  Uninstall SysPathSleuth from both user-site and/or system-"
                in result.out
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
                "error: argument -u/--uninstall: not allowed with argument -i/--install" in
                result.err
        )


def test_main(capsys):
    syspath_sleuth.main(["-u"])
    results: CaptureResult = capsys.readouterr()
    # assert results.out == "{'install': False, 'uninstall': True}\n"


def test_append_sleuth_to_customize(request, caplog):
    caplog.set_level(logging.INFO)
    site_customize_path = Path('yow')

    def fin():
        if site_customize_path.exists():
            site_customize_path.unlink()
    request.addfinalizer(finalizer=fin)

    syspath_sleuth.create_site_customize(site_customize_path)
    syspath_sleuth.append_sleuth_to_customize(site_customize_path)
    record: logging.LogRecord
    for record in caplog.get_records('call'):
        if 'Appending SysPathSleuth to system site customize: yow' in record.message:
            assert record.levelname == 'INFO'
            break
    else:
        pytest.fail("Did not find expected log record.")

    assert site_customize_path.exists()
    src_lines: List[str]
    src_lines, _ = inspect.getsourcelines(syspath_sleuth.syspath_sleuth)

    with site_customize_path.open() as site_customize_path_f:
        site_customize_lines: List[str] = site_customize_path_f.readlines()

    assert src_lines == site_customize_lines


def test_get_system_customize_path():
    system_customize_path: Path = syspath_sleuth.get_system_customize_path()
    assert system_customize_path and system_customize_path.name == "sitecustomize.py" and \
           system_customize_path.parent.stem == "site-packages" and \
           "python" in system_customize_path.parent.parent.stem


def test_create_site_customize(request, caplog):
    test_path = Path("yow.yowsa")

    def fin():
        if test_path.exists():
            test_path.unlink()

    request.addfinalizer(finalizer=fin)

    syspath_sleuth.create_site_customize(Path("yow.yowsa"))

    record: logging.LogRecord
    for record in caplog.get_records('call'):
        if 'Creating system site: yow.yowsa' in record.message:
            assert record.levelname == 'INFO'
            break

    assert test_path.exists()
