import atexit

import runtime_syspath
import syspath_sleuth

syspath_sleuth.inject_sleuth()


def uninstall_syspath_sleuth():
    syspath_sleuth.uninstall_sleuth()


atexit.register(uninstall_syspath_sleuth)

if __name__ == "__main__":
    runtime_syspath.add_srcdirs_to_syspath()
    runtime_syspath.print_syspath(sort=False)

    import runtime_syspath_ex

    runtime_syspath_ex.go_main_go()
    runtime_syspath.print_syspath(sort=False)
