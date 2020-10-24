from runtime_syspath.syspath_sleuth import syspath_sleuth_main, is_install_on_import

if __name__ == "__main__" and not is_install_on_import():
    # pylint: disable=no-value-for-parameter
    syspath_sleuth_main()
