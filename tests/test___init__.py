import argparse
import logging

from _pytest.capture import CaptureResult
import pytest

import syspath_sleuth


def test_parse_args_install():
    parser = argparse.ArgumentParser()
    arg_namespace: argparse.Namespace = syspath_sleuth.parse_syspath_sleuth_args(['-i'], parser)

    assert arg_namespace is not None and arg_namespace.install

    parser = argparse.ArgumentParser()
    arg_namespace: argparse.Namespace = syspath_sleuth.parse_syspath_sleuth_args(['--install'],
                                                                                 parser)

    assert arg_namespace is not None and arg_namespace.install


def test_parse_args_uninstall():
    parser = argparse.ArgumentParser()
    arg_namespace: argparse.Namespace = syspath_sleuth.parse_syspath_sleuth_args(['-u'], parser)

    assert arg_namespace is not None and arg_namespace.uninstall

    parser = argparse.ArgumentParser()
    arg_namespace: argparse.Namespace = syspath_sleuth.parse_syspath_sleuth_args(['--uninstall'],
                                                                                 parser)

    assert arg_namespace is not None and arg_namespace.uninstall


def test_parse_args_help(capsys):
    try:
        syspath_sleuth.parse_syspath_sleuth_args(['-h'], argparse.ArgumentParser())

        pytest.fail("'-h' should exit.")
    except SystemExit:
        result: CaptureResult = capsys.readouterr()
        assert 'usage:' in result.out and '(-i | -u)' in result.out
        assert '-i, --install    Install SysPathSleuth to user-site if available, else' in \
               result.out
        assert '-u, --uninstall  Uninstall SysPathSleuth from both user-site and/or system-' in \
               result.out


def test_parse_args_bad(capsys):
    try:
        argparse.Namespace = syspath_sleuth.parse_syspath_sleuth_args(None,
                                                                      argparse.ArgumentParser())
        pytest.fail('At lease one arg is required.')
    except SystemExit:
        result: CaptureResult = capsys.readouterr()
        assert 'usage:' in result.err and '(-i | -u)' in result.err
        assert 'error: one of the arguments -i/--install -u/--uninstall is required' in result.err

    try:
        syspath_sleuth.parse_syspath_sleuth_args(['-i', '-u'], argparse.ArgumentParser())
        pytest.fail("'-i' and '-u' are mutually exclusive.")
    except SystemExit:
        result: CaptureResult = capsys.readouterr()
        assert 'usage:' in result.err and '(-i | -u)' in result.err
        assert 'error: argument -u/--uninstall: not allowed with argument -i/--install' in result.err


def test_main(capsys):
    syspath_sleuth.main(['-u'])
    results: CaptureResult = capsys.readouterr()
    # assert results.out == "{'install': False, 'uninstall': True}\n"
