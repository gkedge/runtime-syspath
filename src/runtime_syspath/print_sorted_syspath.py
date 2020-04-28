""" print_sort_syspath module """
import sys


def print_sorted_syspath() -> None:
    """
    Print out the current sys.path reverse sorted.
    :return:
    """
    print('\nsys.path:')
    for path in sorted(sys.path, reverse=True):
        print(f'\t{path}')
