"""
Checking a subproject in a subproject package
"""
from typing import Optional, Tuple

from runtime_syspath import get_package_and_max_relative_import_dots

(
    FULLY_QUALIFIED_PACKAGE,
    MAX_RELATIVE_IMPORT_DOTS,
) = get_package_and_max_relative_import_dots(__name__)


def number_of_dots_up_to_relatively_import_on_import() -> Tuple[
    Optional[str], Optional[str]
]:
    """
    try to import test_subproject_package_mod
    :return:
    """
    # pylint: disable=import-outside-toplevel,relative-beyond-top-level
    from .. import test_subproject_package_mod

    # pylint: enable=import-outside-toplevel,relative-beyond-top-level

    return (
        test_subproject_package_mod.FULLY_QUALIFIED_PACKAGE,
        test_subproject_package_mod.MAX_RELATIVE_IMPORT_DOTS,
    )
