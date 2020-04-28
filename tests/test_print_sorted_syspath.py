""" test print_sort_syspath module """
import re
from typing import List

import pytest

from runtime_syspath import filtered_sorted_syspath, print_syspath


@pytest.mark.parametrize("path_filter", [None, r'test_subproject'])
@pytest.mark.parametrize("sort", [True, False])
@pytest.mark.parametrize("no_filtering", [True, False])
def test_filtered_sorted_syspath(path_filter: str, no_filtering: bool, sort: bool):
    """ Run print_sorted_syspath. """
    paths: List[str] = filtered_sorted_syspath(re.compile(path_filter) if path_filter else None,
                                               no_filtering=no_filtering, sort=sort)

    assert len(paths) > 0


@pytest.mark.parametrize("path_filter", [None, r'test_subproject'])
@pytest.mark.parametrize("sort", [True, False])
@pytest.mark.parametrize("no_filtering", [True, False])
def test_print_syspath(path_filter: str, no_filtering: bool, sort: bool):
    """ Run print_syspath. """
    print_syspath(re.compile(path_filter) if path_filter else None,
                  no_filtering=no_filtering, sort=sort)
