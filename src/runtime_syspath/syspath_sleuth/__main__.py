#!/usr/bin/env python3

from . import syspath_sleuth_main, is_install_on_import

# pylint: disable=no-value-for-parameter
if not is_install_on_import():
    syspath_sleuth_main()
