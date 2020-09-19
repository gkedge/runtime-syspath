import inspect
import logging
import site
import sys
from pathlib import Path, PurePath
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
        return super().remove(*args)

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

        frame_info: Optional[inspect.Traceback] = None
        # Only inspect the slooow stack introspection if print()'ing or logging level is sufficient.
        if not cls._is_logging_on() or cls.logger.isEnabledFor(logging.INFO):
            syspath_caller: FrameType = inspect.currentframe().f_back.f_back
            if not (inspect.istraceback(syspath_caller) or inspect.isframe(syspath_caller)):
                return
            frame_info: inspect.Traceback = inspect.getframeinfo(syspath_caller)

        if frame_info:
            message = f"sys.path.{action}{args} from {frame_info.filename}:{frame_info.lineno}"
            cls._inform_user(message)

    @classmethod
    def _is_logging_on(cls):
        is_logging_on = cls.logger.getEffectiveLevel() != logging.NOTSET
        if is_logging_on:
            handler: logging.Handler
            for handler in cls.logger.handlers:
                if handler.level != logging.NOTSET:
                    break
            else:
                is_logging_on = False
        return is_logging_on

    @classmethod
    def _inform_user(cls, message: str, logging_level: int = logging.INFO):
        if cls._is_logging_on() and cls.logger.isEnabledFor(logging_level):
            cls.logger.log(logging_level, message)
        else:
            print(f"{logging.getLevelName(logging_level)}: {message})")

    @classmethod
    def is_sleuth_active(cls):
        sleuth_module_file_name = PurePath(__file__).name
        # Do both so report informs user whether it has been installed both.
        is_active_in_user_site = cls._is_active_in_user_site(sleuth_module_file_name)
        is_active_in_system_site = cls._is_active_in_system_site(sleuth_module_file_name)

        return is_active_in_user_site or is_active_in_system_site

    @staticmethod
    def get_user_customize_path() -> Path:
        user_customize_module_name = PurePath("usercustomize.py")
        sleuth_user_path = Path(site.getusersitepackages()) / user_customize_module_name
        return sleuth_user_path

    @staticmethod
    def get_system_customize_path() -> Optional[Path]:
        site_customize_module_name = PurePath("sitecustomize.py")

        system_site: str
        for system_site in site.getsitepackages():
            system_site_path: Path = Path(system_site)
            if system_site_path.name == "site-packages" and system_site_path.is_dir():
                return system_site_path / site_customize_module_name
        return None

    @classmethod
    def _is_active_in_user_site(cls, sleuth_module_file_name):
        # When using venv, site.ENABLE_USER_SITE is False. When using virtual environments,
        # the effort is to isolate the activities within one virtual environment per Python
        # system Python from other virtual environments. Were the user site enabled, it would
        # affect other Python virtual environments.
        if not site.ENABLE_USER_SITE or not site.check_enableusersite():
            return False

        if sleuth_module_file_name != "usercustomize.py":
            # It is likely syspath_sleuth.py is being tested
            return False

        sleuth_user_path = cls.get_user_customize_path()
        if not sleuth_user_path.exists():
            return False

        sleuth_message = f"SysPathSleuth is installed in user site packages: {sleuth_user_path}"
        cls._inform_user(sleuth_message, logging_level=logging.WARNING)
        return True

    @classmethod
    def _is_active_in_system_site(cls, sleuth_module_file_name):
        if sleuth_module_file_name != "sitecustomize.py":
            # It is likely syspath_sleuth.py is being tested
            return False

        sleuth_system_path = cls.get_system_customize_path()
        if not sleuth_system_path or not sleuth_system_path.exists():
            return False

        sleuth_message = f"SysPathSleuth is installed in system site packages: {sleuth_system_path}"
        cls._inform_user(sleuth_message, logging_level=logging.WARNING)
        return True


# Might be pytest'ing...
if SysPathSleuth.is_sleuth_active():
    sys.path = SysPathSleuth(sys.path)
