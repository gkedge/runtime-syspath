import inspect
import logging
from pathlib import Path, PurePath
from typing import List

from _pytest.capture import CaptureFixture
from _pytest.logging import LogCaptureFixture

from syspath_sleuth import SysPathSleuth


def test_append_print(capsys: CaptureFixture):
    sleuth = SysPathSleuth()
    sleuth.append("yow")
    currentframe = inspect.currentframe()
    assert currentframe, "No current frame?"
    # If this call to get a Traceback on the current frame is moved to a point where it isn't 6
    # lines from 'sleuth.append above, test will fail until the traceback.lineno is adjusted
    # accordingly.
    traceback: inspect.Traceback = inspect.getframeinfo(currentframe)

    assert len(sleuth) == 1 and sleuth == ["yow"]
    out: str = capsys.readouterr().out
    out_lines: List[str] = out.splitlines(keepends=False)
    assert len(out_lines) == 1, "Unexpected line count"
    message: str = out_lines[0]
    assert message.startswith("sys.path.append('yow',)")
    filename = PurePath(traceback.filename).relative_to(Path.cwd())
    assert f"{filename}:{traceback.lineno - 6}" in message


def test_append_logger(caplog: LogCaptureFixture):
    caplog.handler.setLevel(logging.DEBUG)
    sleuth = SysPathSleuth()
    sleuth.config_logger(handler=caplog.handler, level=logging.DEBUG)
    sleuth.append("yow")
    currentframe = inspect.currentframe()
    assert currentframe, "No current frame?"
    # If this call to get a Traceback on the current frame is moved to a point where it isn't 6
    # lines from 'sleuth.append above, test will fail until the traceback.lineno is adjusted
    # accordingly.
    traceback: inspect.Traceback = inspect.getframeinfo(currentframe)

    assert len(sleuth) == 1 and sleuth == ["yow"]
    log_records: List[logging.LogRecord] = caplog.records
    assert len(log_records) == 1, "Unexpected log count."
    message: str = log_records[0].getMessage()
    assert message.startswith("sys.path.append('yow',)")
    filename = PurePath(traceback.filename).relative_to(Path.cwd())
    assert f"{filename}:{traceback.lineno - 6}" in message


def test_is_sleuth_active():
    assert not SysPathSleuth.is_sleuth_active()


def test_get_base_list():
    sleuth = SysPathSleuth()
    sleuth.append("yow")

    base_list = sleuth.get_base_list()
    assert not isinstance(base_list, SysPathSleuth)
    assert "yow" in base_list and len(base_list) == 1
