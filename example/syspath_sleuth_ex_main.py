#! /usr/bin/env python3

import atexit
import logging
import sys

from runtime_syspath import syspath_sleuth

logger: logging.Logger = logging.getLogger(__file__)
LOGGER_LEVEL = logging.INFO
logger.setLevel(LOGGER_LEVEL)

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

    consoleHandler: logging.Handler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(LOGGER_LEVEL)

    sys.path.config_logger(handler=consoleHandler, level=LOGGER_LEVEL)

    import runtime_syspath

    runtime_syspath.print_syspath(sort=False)

    for path in sys.path:
        if path.endswith("runtime-syspath/src"):
            logger.warning(
                "Since this script is run with '/project-root/src' in 'sys.path', "
                "\n\tno report of its addition will be made by "
                "runtime_syspath.add_srcdirs_to_syspath()\n"
            )
    runtime_syspath.add_srcdirs_to_syspath()

    runtime_syspath.print_syspath(sort=False)

    import runtime_syspath_ex

    runtime_syspath_ex.go_main_go()
    runtime_syspath.print_syspath(sort=False)
