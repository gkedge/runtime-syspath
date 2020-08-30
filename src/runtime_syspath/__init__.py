""" __init__ module. """
import re

from .syspath_utils import (
    add_srcdirs_to_syspath,
    filtered_sorted_syspath,
    get_package_and_max_relative_import_dots,
    init_std_syspath_filter,
    print_syspath,
)

__version__ = "0.1.35"

init_std_syspath_filter(re.compile(r"([Jj]et[Bb]rains|[Pp]ython|PyCharm|v\w*env)"))
