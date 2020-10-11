import inspect
import logging
import os
import site
import sys
from pathlib import Path, PurePath
from types import FrameType
from typing import List, Optional


class SysPathSleuth(list):
    logger: logging.Logger = logging.getLogger("runtime-syspath.SysPathSleuth")
    logger.setLevel(logging.NOTSET)
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
    def is_sleuth_active(cls):
        sleuth_module_file_name = PurePath(__file__).name
        # Do both so report informs user whether it has been installed both.
        is_active_in_user_site = cls._is_active_in_user_site(sleuth_module_file_name)
        is_active_in_system_site = cls._is_active_in_system_site(sleuth_module_file_name)
        is_syspath_sleuth_kill = False
        if is_active_in_user_site or is_active_in_system_site:
            is_syspath_sleuth_kill = os.getenv("SYSPATH_SLEUTH_KILL") is not None
            if is_syspath_sleuth_kill:
                cls._inform_user(
                    f"SysPathSleuth is installed in site customize, "
                    f"but disabled due to $SYSPATH_SLEUTH_KILL env var: "
                    f"{is_syspath_sleuth_kill}"
                )

        return not is_syspath_sleuth_kill and (is_active_in_user_site or is_active_in_system_site)

    @staticmethod
    def relative_path(customize_path):
        try:
            customize_path = customize_path.relative_to(sys.base_prefix)
        except ValueError:
            customize_path_orig = customize_path
            cwd = Path.cwd()
            while customize_path == customize_path_orig:
                try:
                    customize_path = customize_path.relative_to(cwd)
                    break
                except ValueError:
                    if str(cwd) == "/":
                        break
                    cwd = cwd.parent
        return customize_path

    def get_base_list(self) -> List[str]:
        return list(self)

    @classmethod
    def config_logger(cls, handler: logging.Handler = None, level: int = -1):
        if level != -1:
            cls.logger.setLevel(level)
        if handler:
            cls.logger.addHandler(handler)
            if cls.logger.getEffectiveLevel() < handler.level:
                logger_level_name = logging.getLevelName(cls.logger.getEffectiveLevel())
                handler_level_name = logging.getLevelName(handler.level)
                message = (
                    f"Handler's level ({handler_level_name}) is insufficient "
                    f"to log at {cls.logger.name}'s level ({logger_level_name}) yet."
                )
                cls._inform_user(message)

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
            filename = PurePath(frame_info.filename)
            try:
                filename = PurePath(frame_info.filename).relative_to(sys.base_prefix)
            except ValueError:
                filename_orig = filename
                cwd = Path.cwd()
                while filename == filename_orig:
                    try:
                        filename = PurePath(frame_info.filename).relative_to(cwd)
                        break
                    except ValueError:
                        cwd = cwd.parent

            message = f"sys.path.{action}{args} from {filename}:{frame_info.lineno}"
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
            print(message)

    @staticmethod
    def _get_user_customize_path() -> Path:
        user_customize_module_name = PurePath("usercustomize.py")
        user_customize_path = Path(site.getusersitepackages()) / user_customize_module_name
        return user_customize_path

    @staticmethod
    def _get_system_customize_path() -> Optional[Path]:
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

        user_customize_path = cls._get_user_customize_path()
        if not user_customize_path.exists():
            return False
        user_customize_path = cls.relative_path(user_customize_path)
        sleuth_message = f"SysPathSleuth is installed in user site: {user_customize_path}"
        cls._inform_user(sleuth_message)
        return True

    @classmethod
    def _is_active_in_system_site(cls, sleuth_module_file_name):
        if sleuth_module_file_name != "sitecustomize.py":
            # It is likely syspath_sleuth.py is being tested
            return False

        system_custom_path = cls._get_system_customize_path()
        if not system_custom_path or not system_custom_path.exists():
            return False

        system_custom_path = cls.relative_path(system_custom_path)
        sleuth_message = f"SysPathSleuth is installed in system site: {system_custom_path}"
        cls._inform_user(sleuth_message)
        return True


# Might be pytest'ing...
if SysPathSleuth.is_sleuth_active():
    sys.path = SysPathSleuth(sys.path)
