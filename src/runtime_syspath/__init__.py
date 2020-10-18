""" __init__ module. """
import re

from .syspath_path_utils import get_project_root_dir
from .syspath_utils import (
    add_srcdirs_to_syspath,
    filtered_sorted_syspath,
    get_package_and_max_relative_import_dots,
    init_std_syspath_filter,
    persist_syspath,
    print_syspath,
)

init_std_syspath_filter(re.compile(r"([Jj]et[Bb]rains|[Pp]ython|PyCharm|v\w*env)"))
