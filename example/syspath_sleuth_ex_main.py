#! /usr/bin/env python3

import atexit
import logging
import sys

import syspath_sleuth

logger: logging.Logger = logging.getLogger(__file__)
level = logging.INFO
logger.setLevel(level)

syspath_sleuth.inject_sleuth()


def uninstall_syspath_sleuth():
    syspath_sleuth.uninstall_sleuth()


atexit.register(uninstall_syspath_sleuth)

if __name__ == "__main__":

    # START Sanity Test; not necessary for real use!
    # pylint: disable=import-outside-toplevel
    import sitecustomize

    # pylint: enable=import-outside-toplevel

    if not isinstance(sys.path, sitecustomize.SysPathSleuth):
        sys.exit("Expected sys.path to be monkey-patched.")
    # END Sanity Test

    consoleHandler: logging.Handler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(level)

    sys.path.config_logger(handler=consoleHandler, level=level)

    import runtime_syspath

    runtime_syspath.print_syspath(sort=False)

    for path in sys.path:
        if path.endswith('runtime-syspath/src'):
            logger.warning("Since this script is run with '/project-root/src' in 'sys.path', "
                           "\n\tno report of its addition will be made by "
                           "runtime_syspath.add_srcdirs_to_syspath()\n")
    runtime_syspath.add_srcdirs_to_syspath()

    runtime_syspath.print_syspath(sort=False)

    import runtime_syspath_ex

    runtime_syspath_ex.go_main_go()
    runtime_syspath.print_syspath(sort=False)
