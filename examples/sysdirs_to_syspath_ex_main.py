#! /usr/bin/env python3

import runtime_syspath

runtime_syspath.add_srcdirs_to_syspath()
runtime_syspath.print_syspath(sort=False)

if __name__ == "__main__":

    import runtime_syspath_ex

    runtime_syspath_ex.go_main_go()
    runtime_syspath.print_syspath(sort=False)
    runtime_syspath.print_syspath()
