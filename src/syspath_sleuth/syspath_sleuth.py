import logging
from pathlib import PurePath, Path
import site
import sys

import inspect
from types import FrameType
from typing import Optional


class SysPathSleuth(list):
    logger: logging.Logger = logging.getLogger("runtime-syspath.SysPathSleuth")
    logger.propagate = False

    def insert(self, *args):
        self._where("insert", args)
        return super().insert(*args)

    def append(self, *args):
        self._where("append", args)
        return super().append(*args)

    def extend(self, *args):
        self._where("extend", args)
        return super().extend(*args)

    def pop(self, *args):
        self._where("pop", args)
        return super().pop(*args)

    def remove(self, *args):
        self._where("remove", args)
        return super().pop(*args)

    def __delitem__(self, *args):
        self._where("__delitem__", args)
        return super().__delitem__(*args)

    def __setitem__(self, *args):
        self._where("__setitem__", args)
        return super().__setitem__(*args)

    @classmethod
    def config_logger(cls, handler: logging.Handler = None, level: int = -1):
        if level != -1:
            cls.logger.setLevel(level)
        if handler:
            cls.logger.addHandler(handler)
            if not cls.logger.isEnabledFor(handler.level):
                level_name = logging.getLevelName(cls.logger.getEffectiveLevel())
                logger_message = (
                    f"{cls.logger.name}'s logger level ({level_name}) is not sufficient to "
                    f"leverage passed handler's level ({handler.level}) yet."
                )
                cls._inform_user(logger_message)

    @classmethod
    def _where(cls, action, args):
        is_logging_on = cls._is_logging_on()

        frame_info: Optional[inspect.Traceback] = None
        if not is_logging_on or cls.logger.isEnabledFor(logging.INFO):
            syspath_caller: FrameType = inspect.currentframe().f_back.f_back
            if not (inspect.istraceback(syspath_caller) or inspect.isframe(syspath_caller)):
                return
            frame_info: inspect.Traceback = inspect.getframeinfo(syspath_caller)

        if frame_info:
            message = f"sys.path.{action}{args} from {frame_info.filename}:{frame_info.lineno}"
            cls._inform_user(message, is_logging_on=is_logging_on)

    @classmethod
    def _is_logging_on(cls):
        is_logging_on = cls.logger.getEffectiveLevel() != logging.NOTSET
        if is_logging_on:
            for handler in cls.logger.handlers:
                if handler.level != logging.NOTSET:
                    break
            else:
                is_logging_on = False
        return is_logging_on

    @classmethod
    def _inform_user(
        cls, message: str, is_logging_on: Optional[bool] = None, logging_level: int = logging.INFO
    ):
        if cls._is_logging_on() if is_logging_on is None else is_logging_on:
            cls.logger.log(logging_level, message)
        else:
            print(f"{logging.getLevelName(logging_level)}: {message})")

    @classmethod
    def is_sleuth_active(cls):
        sleuth_module_file_name = PurePath(__file__).name
        # Do both so report informs user whether it has been installed both.
        is_active_in_user_site = cls.is_active_in_user_site(sleuth_module_file_name)
        is_active_in_system_site = cls.is_active_in_system_site(sleuth_module_file_name)

        return is_active_in_user_site or is_active_in_system_site

    @classmethod
    def is_active_in_user_site(cls, sleuth_module_file_name):
        is_active_in_user_site = False
        # Determine if user site is available and enabled. If so, report if the
        # sleuth_module_file_name is the usercustomize.py module within the user site.
        if site.check_enableusersite() and site.ENABLE_USER_SITE:
            if sleuth_module_file_name == "usercustomize.py":
                user_customize_module_name = PurePath(sleuth_module_file_name)
                sleuth_user_path = Path(site.getusersitepackages()) / user_customize_module_name
                is_active_in_user_site = sleuth_user_path.exists()
                if is_active_in_user_site:
                    sleuth_message = (
                        f"SysPathSleuth is installed in user site packages: {sleuth_user_path}"
                    )
                    SysPathSleuth._inform_user(sleuth_message, logging_level=logging.WARNING)
        return is_active_in_user_site

    @classmethod
    def is_active_in_system_site(cls, sleuth_module_file_name):
        is_active_in_system_site = False
        # Report if the sleuth_module_file_name is the sitecustomize.py module within any of the
        # site packages directories.
        if sleuth_module_file_name == "sitecustomize.py":
            site_customize_module_name = PurePath("sitecustomize.py")
            for site_package in site.getsitepackages():
                site_package_path: Path = Path(site_package)
                if not site_package_path.is_dir():
                    continue
                sleuth_system_path = site_package_path / site_customize_module_name
                is_active_in_system_site = sleuth_system_path.exists()
                if not is_active_in_system_site:
                    continue
                sleuth_message = (
                    f"SysPathSleuth is installed in system site packages: {sleuth_system_path}"
                )
                SysPathSleuth._inform_user(sleuth_message, logging_level=logging.WARNING)
                break
        return is_active_in_system_site


# Might be pytest'ing...
if SysPathSleuth.is_sleuth_active():
    sys.path = SysPathSleuth(sys.path)
