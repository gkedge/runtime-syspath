""" print_sort_syspath module """
import re
import sys
from typing import Pattern, List, Union

_STD_SYSPATH_FILTER: Union[None, Pattern] = None


def init_std_syspath_filter(std_syspath_filter: Pattern) -> None:
    """
    Provide a globally bound standard filter Pattern applied to all subsequent sys.path filtering
    operations.  Note: a init_std_syspath_filter() is called from __init__.py to default to a
    globally applied pattern.
    :param std_syspath_filter: pattern to apply to all filter operations. Can be None.
    :return: None
    """
    # pylint: disable=global-statement
    global _STD_SYSPATH_FILTER
    # pylint: enable=global-statement
    _STD_SYSPATH_FILTER = std_syspath_filter


def filtered_sorted_syspath(path_filter: Pattern = None,
                            no_filtering: bool = False, sort: bool = False) -> List[str]:
    """
    Filter and sort the syspath for only paths of interest.
    :param path_filter: a pattern that the user can provide in addition to the std_syspath_filter
    :param no_filtering: allow user to not filter at all
    :param sort: allow user to sort the filtered (if filtering) sys.path
    :return: sys.path with filtering and sorting applied
    """
    paths: List[str] = sys.path
    if not no_filtering:
        # pylint: disable=global-statement
        global _STD_SYSPATH_FILTER
        # pylint: enable=global-statement
        if _STD_SYSPATH_FILTER:
            paths = [p for p in paths if not re.search(_STD_SYSPATH_FILTER, p)]
        if path_filter:
            paths = [p for p in paths if not re.search(path_filter, p)]

    return sorted(paths, reverse=True) if sort else paths


def print_syspath(path_filter: Pattern = None,
                  no_filtering: bool = False, sort: bool = True) -> None:
    """
    Filter and sort the syspath for only paths of interest.
    :param path_filter: a pattern that the user can provide in addition to the std_syspath_filter
    :param no_filtering: allow user to not filter at all
    :param sort: allow user to sort the filtered (if filtering) sys.path
    :return: None
    """
    paths: List[str] = filtered_sorted_syspath(path_filter, no_filtering, sort)
    print(f'\nsys.path({len(paths)} paths):')
    for path in paths:
        print(f'\t{path}')
