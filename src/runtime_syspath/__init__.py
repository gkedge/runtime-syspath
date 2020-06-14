# pylint: disable=invalid-name
""" __init__ module. """
import re

# noinspection PyUnresolvedReferences
# pylint: disable=import-error
from .syspath_utils import add_srcdirs_to_syspath, init_std_syspath_filter, \
    filtered_sorted_syspath, print_syspath, get_package_and_max_relative_import_dots  # noqa

# pylint: enable=import-error

__version__ = '0.1.12'

init_std_syspath_filter(re.compile(r'([Jj]et[Bb]rains|[Pp]ython|PyCharm|v\w*env)'))
