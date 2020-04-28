# pylint: disable=invalid-name
""" __init__ module. """
import re

from .add_srcdirs_to_syspath import add_srcdirs_to_syspath  # noqa
from .print_sorted_syspath import init_std_syspath_filter, filtered_sorted_syspath, \
    print_syspath  # noqa

# noinspection PyUnresolvedReferences
# pylint: disable=import-error

__version__ = '0.1.0'

init_std_syspath_filter(re.compile(r'(Python|PyCharm|Cache)'))
