"""
Check subproject import
"""
from runtime_syspath import get_package_and_max_relative_import_dots

(
    FULLY_QUALIFIED_PACKAGE,
    MAX_RELATIVE_IMPORT_DOTS,
) = get_package_and_max_relative_import_dots(__name__)
