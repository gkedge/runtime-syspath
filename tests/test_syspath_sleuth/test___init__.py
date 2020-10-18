import importlib
import inspect
import logging
import os
import re
import site
import sys
from importlib import reload
from pathlib import Path
from typing import List, Tuple

import pytest
from _pytest.fixtures import FixtureRequest
from click.testing import CliRunner, Result

import runtime_syspath
from runtime_syspath import syspath_sleuth
from runtime_syspath.syspath_sleuth import SysPathSleuth, get_customize_path


def test_parse_args_help():
    runner = CliRunner()
    result: Result = runner.invoke(syspath_sleuth.syspath_sleuth_main, ["--help"])
    assert "Usage:" in result.stdout
    assert "-i, --inject" in result.stdout and "-u, --uninstall" in result.stdout
    assert "-c, --custom" in result.stdout
    assert "-v, --verbose" in result.stdout


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

    request.addfinalizer(finalizer=fin)
    fin()  # run ahead in case failed tests left junk

    syspath_sleuth.create_site_customize(test_path)

    record: logging.LogRecord
    for record in caplog.get_records("call"):
        if "Creating system site: yow.yowsa" in record.message:
            assert record.levelname == "WARNING"
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
    fin()  # run ahead in case failed tests left junk

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
    fin()  # run ahead in case failed tests left junk

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
    src_lines, _ = inspect.getsourcelines(runtime_syspath.syspath_sleuth.syspath_sleuth)

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
    fin()  # run ahead in case failed tests left junk

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
    fin()  # run ahead in case failed tests left junk

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
    assert not customize_path.exists()

    record: logging.LogRecord
    for record in caplog.get_records("call"):
        if f"Removing {SysPathSleuth.__name__} from site customize: yow" in record.message:
            assert record.levelname == "INFO"
            break
    else:
        pytest.fail("Did not find expected log record.")


def test_inject_sleuth(request, caplog):
    caplog.set_level(logging.INFO)
    customize_path, _ = get_customize_path()
    copied_customize_path = customize_path.with_suffix(syspath_sleuth.PRE_SLEUTH_SUFFIX)
    reverse_patch_path = customize_path.with_suffix(syspath_sleuth.REVERSE_PATCH_SUFFIX)

    def fin():
        if customize_path.exists():
            customize_path.unlink()
        if reverse_patch_path.exists():
            reverse_patch_path.unlink()

    request.addfinalizer(finalizer=fin)
    fin()  # run ahead in case failed tests left junk

    syspath_sleuth.inject_sleuth()
    assert customize_path.exists() and customize_path.stat().st_size != 0
    assert reverse_patch_path.exists() and reverse_patch_path.stat().st_size != 0
    assert not copied_customize_path.exists()
    with customize_path.open() as customize_f:
        assert f"class {SysPathSleuth.__name__}" in customize_f.read()

    creating_message = "Creating system site sitecustomize.py"
    append_message = (
        f"Appending {SysPathSleuth.__name__} to site customize: "
        f"{SysPathSleuth.relative_path(customize_path)}"
    )
    record: logging.LogRecord
    for record, message in zip(caplog.get_records("call"), [creating_message, append_message]):
        assert message in record.getMessage(), "Did not find expected log record message."
        assert record.levelname == "INFO", "Did not find expected log record level."

    caplog.clear()

    # Inject a second time; should remove existing and re-append SysPathSleuth
    syspath_sleuth.inject_sleuth()
    assert customize_path.exists() and customize_path.stat().st_size != 0
    assert reverse_patch_path.exists() and reverse_patch_path.stat().st_size != 0
    assert not copied_customize_path.exists()
    with customize_path.open() as customize_f:
        assert f"class {SysPathSleuth.__name__}" in customize_f.read()

    reinstalling_message = "Reinstalling SysPathSleuth in system site..."
    create_message = "Creating system site sitecustomize.py"

    removing_message = (
        f"Removing {SysPathSleuth.__name__} from site customize: "
        f"{SysPathSleuth.relative_path(customize_path)}"
    )
    append_message = (
        f"Appending {SysPathSleuth.__name__} to site customize: "
        f"{SysPathSleuth.relative_path(customize_path)}"
    )
    record: logging.LogRecord
    for record, message in zip(
        caplog.records, [reinstalling_message, removing_message, create_message, append_message]
    ):
        assert record.getMessage() == message, "Did not find expected log record message."
        if message in create_message or message in removing_message or message in append_message:
            assert record.levelname == "INFO", "Did not find expected log record level."
            continue
        assert record.levelname == "WARNING", "Did not find expected log record level."


def test_uninstall_sleuth(request, caplog):
    customize_path, _ = get_customize_path()
    reverse_patch_path = customize_path.with_suffix(syspath_sleuth.REVERSE_PATCH_SUFFIX)

    def fin():
        if customize_path.exists():
            customize_path.unlink()

    request.addfinalizer(finalizer=fin)
    fin()  # run ahead in case failed tests left junk

    caplog.set_level(logging.NOTSET)
    syspath_sleuth.inject_sleuth()

    caplog.clear()

    caplog.set_level(logging.INFO)
    syspath_sleuth.uninstall_sleuth()
    assert not customize_path.exists()
    assert not reverse_patch_path.exists()

    removing_message = (
        f"Removing {SysPathSleuth.__name__} from site customize: "
        f"{SysPathSleuth.relative_path(customize_path)}"
    )
    uninstalled_message = (
        f"SysPathSleuth uninstalled from system site: "
        f"{SysPathSleuth.relative_path(customize_path)}"
    )
    record: logging.LogRecord
    for record, message in zip(caplog.records, [removing_message, uninstalled_message]):
        assert message in record.getMessage(), "Did not find expected log record message."
        if message in removing_message:
            assert record.levelname == "INFO", "Did not find expected log record level."
            continue
        assert record.levelname == "WARNING", "Did not find expected log record level."

    assert len(caplog.records) == 2
    caplog.clear()

    # Uninstall a second time; should be a noop
    syspath_sleuth.uninstall_sleuth()
    assert not customize_path.exists()
    assert not reverse_patch_path.exists()

    was_not_installed_message = (
        f"SysPathSleuth was not installed in system site: "
        f"{SysPathSleuth.relative_path(customize_path)}"
    )
    record: logging.LogRecord
    for record, message in zip(caplog.records, [was_not_installed_message]):
        assert message in record.getMessage(), "Did not find expected log record message."
        assert record.levelname == "WARNING", "Did not find expected log record level."
    assert len(caplog.records) == 1


def test_main(request, caplog):
    caplog.set_level(logging.INFO)

    customize_path, _ = get_customize_path()
    copied_customize_path = customize_path.with_suffix(syspath_sleuth.PRE_SLEUTH_SUFFIX)
    reverse_patch_path = customize_path.with_suffix(syspath_sleuth.REVERSE_PATCH_SUFFIX)

    def fin():
        if customize_path.exists():
            customize_path.unlink()
        if copied_customize_path.exists():
            reverse_patch_path.unlink()
        if reverse_patch_path.exists():
            reverse_patch_path.unlink()

    request.addfinalizer(finalizer=fin)
    fin()  # run ahead in case failed tests left junk

    runner = CliRunner()
    runner.invoke(syspath_sleuth.syspath_sleuth_main, ["-i"])
    assert customize_path.exists() and customize_path.stat().st_size != 0
    assert reverse_patch_path.exists() and reverse_patch_path.stat().st_size != 0
    assert not copied_customize_path.exists()
    assert is_sleuth_active(), (
        f"SysPathSleuth is not active, $SYSPATH_SLEUTH_KILL enabled?: "
        f"{os.getenv('SYSPATH_SLEUTH_KILL') is not None}"
    )

    creating_message = "Creating system site sitecustomize.py"
    append_message = (
        f"Appending {SysPathSleuth.__name__} to site customize: "
        f"{SysPathSleuth.relative_path(customize_path)}"
    )
    record: logging.LogRecord
    for record, message in zip(caplog.get_records("call"), [creating_message, append_message]):
        assert message in record.getMessage(), "Did not find expected log record message."
        assert record.levelname == "INFO", "Did not find expected log record level."

    caplog.clear()

    runner.invoke(syspath_sleuth.syspath_sleuth_main, ["-u"])

    assert not customize_path.exists()
    assert not reverse_patch_path.exists()
    # assert not is_sleuth_active()

    removing_message = (
        f"Removing {SysPathSleuth.__name__} from site customize: "
        f"{SysPathSleuth.relative_path(customize_path)}"
    )
    record: logging.LogRecord
    for record, message in zip(caplog.records, [removing_message]):
        assert message in record.getMessage(), "Did not find expected log record message."
        assert record.levelname == "INFO", "Did not find expected log record level."


def is_sleuth_active():
    if site.ENABLE_USER_SITE and site.check_enableusersite():
        customize_module = importlib.import_module("usercustomize")
    else:
        customize_module = importlib.import_module("sitecustomize")
    reload(customize_module)
    class_names: Tuple[str] = tuple(
        x[0] for x in inspect.getmembers(customize_module, inspect.isclass)
    )
    is_sleuth_active_now = "SysPathSleuth" in class_names and isinstance(
        sys.path, customize_module.SysPathSleuth
    )
    return is_sleuth_active_now


def test_live_report(request: FixtureRequest, testdir):
    test_case_name = request.node.name

    def fin():
        runner.invoke(syspath_sleuth.syspath_sleuth_main, ["-u"])

    request.addfinalizer(finalizer=fin)

    runner = CliRunner()
    runner.invoke(syspath_sleuth.syspath_sleuth_main, ["-i"])
    assert is_sleuth_active(), (
        f"SysPathSleuth is not active, $SYSPATH_SLEUTH_KILL enabled?: "
        f"{os.getenv('SYSPATH_SLEUTH_KILL') is not None}"
    )

    temp_test_py_file = testdir.makepyfile(
        """
        import sys
        sys.path.append("yow")
        sys.path.insert(0, "yowsa")
        sys.path.remove("yow")
        sys.path.pop()
        sys.path.extend(["yow", "yowsa"])
    """
    )
    result = testdir.runpython(temp_test_py_file)

    relevant_index = 0
    regex = r"SysPathSleuth is installed in (system|user) site:"
    assert re.match(regex, result.outlines[relevant_index])

    for index in range(1, len(result.outlines)):
        if "yow" in result.outlines[index]:
            relevant_index = index
            break

    regex = r"sys\.path\.append\(\'yow\',\) from .*%s\.py:2$" % test_case_name
    assert re.match(regex, result.outlines[relevant_index])

    relevant_index += 1
    regex = r"sys\.path\.insert\(0, \'yowsa\'\) from .*%s\.py:3$" % test_case_name
    assert re.match(regex, result.outlines[relevant_index])

    relevant_index += 1
    regex = r"sys\.path\.remove\(\'yow\',\) from .*%s\.py:4$" % test_case_name
    assert re.match(regex, result.outlines[relevant_index])

    relevant_index += 1
    regex = r"sys\.path\.pop\(\) from .*%s\.py:5$" % test_case_name
    assert re.match(regex, result.outlines[relevant_index])

    relevant_index += 1
    regex = r"sys\.path\.extend\(\[\'yow\', \'yowsa\'\],\) from .*%s\.py:6$" % test_case_name
    assert re.match(regex, result.outlines[relevant_index])
