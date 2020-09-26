#! /usr/bin/env python3

import atexit
import logging
import sys

from runtime_syspath import syspath_sleuth

logger: logging.Logger = logging.getLogger(__file__)
LOGGER_LEVEL = logging.INFO
CONSOLE_HANDLER: logging.Handler = logging.StreamHandler(sys.stdout)
logger.setLevel(LOGGER_LEVEL)
CONSOLE_HANDLER.setLevel(LOGGER_LEVEL)
logger.addHandler(CONSOLE_HANDLER)

# Inject SysPathSleuth to report any addition to sys.path. Repeated running removes and reinjects
# SysPathSleuth as a means of altering SysPathSleuth and updating it. Unless there is a change,
# the call is idempotent.
syspath_sleuth.inject_sleuth()


def uninstall_syspath_sleuth():
    # # pylint: disable=import-outside-toplevel
    # import sitecustomize
    #
    # # pylint: enable=import-outside-toplevel
    #
    # # Removing the monkey-patch seems rife with pending disaster if used during running
    # # execution and not about to exit (like this atexit function is about to), and in that case,
    # # is it really worth it(?). But, it seems to work, doing it in your own implementation, YMMV.
    # sys.path = sys.path.get_base_list()
    # if isinstance(sys.path, sitecustomize.SysPathSleuth):
    #     print("Hmmm... expected sys.path NOT to be monkey-patched.")
    syspath_sleuth.uninstall_sleuth()


# Best n
atexit.register(uninstall_syspath_sleuth)

if __name__ == "__main__":

    # START Sanity Test; not necessary for real use!
    # # pylint: disable=import-outside-toplevel
    # import sitecustomize
    #
    # # pylint: enable=import-outside-toplevel
    #
    # if not isinstance(sys.path, sitecustomize.SysPathSleuth):
    #     sys.exit("Expected sys.path to be monkey-patched.")
    # END Sanity Test

    # Now that SysPathSleuth is in place to wrap 'sys.path', a log handler can be provided.
    # If a log handler is not provided, SysPathSleuth will leverage 'print()'
    sys.path.config_logger(handler=CONSOLE_HANDLER, level=LOGGER_LEVEL)

    import runtime_syspath

    runtime_syspath.print_syspath(sort=False)

    for path in sys.path:
        if path.endswith("runtime-syspath/src"):
            logger.warning(
                "Since this script is run with '/project-root/src' in 'sys.path', "
                "\n\tno report of its addition will be made by "
                "runtime_syspath.add_srcdirs_to_syspath()\n"
            )
    # Search for all 'src' directories and add them to sys.path
    runtime_syspath.add_srcdirs_to_syspath()

    runtime_syspath.print_syspath(sort=False)

    import runtime_syspath_ex

    # Call function in package initializer which will add a path to sys.path
    runtime_syspath_ex.go_main_go()
    runtime_syspath.print_syspath(sort=False)
