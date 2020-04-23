""" pytest configuration for this directory (and their sub-directories)"""
import sys
from pathlib import Path

sys.path.append(str(Path.cwd() / 'src'))

# pylint: disable=import-error
# pylint: disable=wrong-import-position
from runtime_syspath import add_srcdirs_to_syspath  # noqa

add_srcdirs_to_syspath()
