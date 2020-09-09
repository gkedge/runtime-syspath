#!/usr/bin/env python3
__version__ = "2019.04.06.001"

import os
import subprocess as sp
import sys
from pathlib import Path

from _typeshed import OpenTextMode


class InstallError(RuntimeError):
    pass


def parse_args():
    """Parse command line arguments, return argparse namespace."""
    import argparse

    parser = argparse.ArgumentParser(
        description="""\
Install a special version of the python command in a new directory.\
"""
    )
    parser.add_argument(
        "basedir",
        metavar="DIR",
        help="""base directory containing the new bin/python command.\
        This directory must not initially exist.""",
    )
    return parser.parse_args()


def check_basedir_doesnt_exist(basedir):
    if basedir.exists():
        raise InstallError("Directory already exists", str(basedir))


def create_directory(dir):
    try:
        dir.mkdir(parents=True)
    except Exception as exc:
        raise InstallError("Cannot create directory", str(dir)) from exc


def get_user_site_dir(basedir):
    env = dict(os.environ)
    env["PYTHONUSERBASE"] = str(basedir)
    output = sp.check_output([sys.executable, "-m", "site", "--user-site"], env=env).decode()
    return Path(output.strip().split("\n")[-1])


def check_is_below_basedir(dir, basedir):
    try:
        dir.relative_to(basedir)
    except ValueError as exc:
        raise InstallError("Expected directory not below basedir", str(dir), str(basedir)) from exc


def main():
    args = parse_args()
    basedir = Path(args.basedir)
    check_basedir_doesnt_exist(basedir)
    create_directory(basedir)
    try:
        user_site_dir = get_user_site_dir(basedir)
        check_is_below_basedir(user_site_dir, basedir)
        create_directory(user_site_dir)
        with (user_site_dir / "usercustomize.py").open("ta") as w:
            with (Path(__file__).parent / "syspath_sleuth.py").open("tr") as r:
                w.write(r.read())

        bindir = basedir / "bin"
        create_directory(bindir)
        python = bindir / "python"
        otm: OpenTextMode = ""
        python.write_text(python_contents.format(executable=sys.executable))
        python.chmod(0o774)
        print(
            """\
The following new command has been successfully created to invoke python:

    {python}

Customize it at startup by adding code in the usercustomize.py file.
The path to this file's parent directory is given by the command

   <interpreter> -m site --user-site

Its value is currently {user_site_dir}
            """.format(
                python=python, user_site_dir=user_site_dir
            )
        )
    except InstallError:
        import shutil

        shutil.rmtree(str(basedir), ignore_errors=True)
        raise


python_contents = """\
#!{executable}
import os
import sys
os.environ['PYTHONUSERBASE'] = os.path.dirname(os.path.dirname(__file__))
os.execv(sys.executable, [sys.executable] + sys.argv[1:])
"""

main()
