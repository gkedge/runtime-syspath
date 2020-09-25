`runtime-syspath` is a package to ease programmatically adding src root
paths to `sys.path`. This is targeted at python test code that needs to
discover a project's solution source to test.

> :exclamation: It is generally **frowned upon** to alter the `sys.path`
> programmatically as it confuses development, especially refactoring.
> Python IDEs can statically determine if a dependent package's import
> statement is left wanting whether a PyPi installation in needed or
> source cannot be discovered through standard Python paths. A static
> analysis tool's *missing import* detection will end up registering
> false-negatives if the import is discovered via dynamic (programmatic)
> additions to `sys.path` at runtime.

*The following description assumes the use of `pytest` unit testing
support and a project file structuring that includes project root
directories named `src` (project solution) and `tests` (project tests of
project source under `src`. Both `src` and `tests` are not intended to
have package initializers (`__init__.py`). Packages therein will
typically have package initializers allowing for test modules to have
that same name (in separate packages). However, as a general rule, test
modules are not intended to import other test modules. Therefore, there
should be no need for `__init__.py`-enabled, relative importation
between test cases or sub-package test cases. `pytest`'s
[default test discovery](https://docs.pytest.org/en/latest/goodpractices.html#test-discovery)
and intended design use negates the need for :*

```
├─ src
│  └─ __init__.py
|  └─ foo.py
├─ tests
│  └─ test_foo.py
│     └─ foo_and_goo
│        └─ __init__.py
│        └─ test_foo.py
│        └─ test_goo.py
└─ setup.py
```
*That structure is based upon
[this guidance](https://blog.ionelmc.ro/2014/05/25/python-packaging/#the-structure).*

When testing solution source in a project, the test cases _could_
statically access the solution source by importing with the `src`
package prefix:

```
import src.packagename.foo
```
Not only does that not feel right at all, that solution implies that
tests are run **only** from the project root, not within the `tests`
directory itself. If the test is run within the `tests` directory, the
`src` package won't be found at runtime.

So, using:
```
import packagename.foo
```
... the `src` directory would need to be programmatically added to the
`sys.path`. This will allow for tests to be run form any working
directory under the `tests` sub-tree.

`runtime_syspath.add_srcdirs_to_syspath()` will discover all `src`
directories under `<project root>/src`. The reason that there may be
more is if your project may be leveraging `git subprojects` under
`<project root>/src` that have their own `src` directories. Those need
to be added to `sys.path` also.

To leverage `runtime-syspath` to add the `src` directory everytime a
test is run, import `runtime-syspath` and run
`add_srcdirs_to_syspath()` in `tests/conftest.py`. (If `tests`
contain more `conftest.py` under its directory tree, the call still only
need appear in the root `test/conftest.py`!):
 ```
 from runtime_syspath import add_srcdirs_to_syspath
 
 add_srcdirs_to_syspath() 
 ```

`add_srcdirs_to_syspath()` will recursively discover **all** `src`
subdirectories under the <project root>. For projects that use `git
submodules`, their `src` directories need to be added to `src.path` for
import access. `git subprojects` could be added to `src` or `tests`
directory trees:

```
├─ src
│  └─ __init__.py
|  └─ projectpackage
│     └─ __init__.py
|     └─ foo.py
|  └─ subproject
|     └─ src
│       └─ __init__.py
|       └─ bar.py
|     └─ tests
├─ tests
│  └─ test_foo.py
|  └─ test_subproject
|     └─ src
│       └─ __init__.py
|       └─ unfoobarrator.py
|     └─ tests
└─ setup.py
```

> :exclamation: Due to the code maintenance and grok'ing mayhem caused
> by indiscriminate runtime additions to `sys.path`, your goal should be
> to limit that anti-pattern to this discovery-of-source aspect for
> import discovery.

> :bulb: Since programmatically adding to a `sys.path` impairs an IDE's
> ability to do static import discovery and leveraging IDE refactoring
> features between the solution source and the test code, an IDE user
> would need to manually mark all `src` directories as such.  
> PyCharm example:
>
> ![image](docs/images/IDE_SetSrc.png)

#### SysPathSleuth; runtime reporting of programmatic `sys.path` access

On a project riddled with programmatically appending source paths to
`sys.path`, a tool to discover which modules are mucking with `sys.path`
and when could prove useful. This discovery can assist with manually
eradicating `sys.path` access in favor of updating imports with
fully-qualified (anchored at but, not including `src`), absolute
module/package names. static tools would then be able to discover the
modules/packages imported.
> Relative paths: There is a place for relative paths when importing
> intra-package modules. But, when importing inter-package modules,
> leveraging fully-qualified, absolute module/package names is a wiser
> play.

SysPathSleuth is a monkey-patch of `sys.path` to report on `sys.path`
access that comes with an installer to install/uninstall SysPathSleuth
into either the user or system site's _customize_ modules
(`~/pathto/user_site/usercustomize.py` or
`/pathto/python/site-packages/sitecustomize.py`). SysPathSleuth can be
installed/uninstalled using:
* python -m syspath_slueth \[--install _or_ --uninstall]
* at the start within a running program

At the start of a running program prior:
```
import atexit
import syspath_sleuth
from runtime-syspath import syspath_slueth

syspath_sleuth.inject_sleuth()
def uninstall_syspath_sleuth():
    syspath_sleuth.uninstall_sleuth()

atexit.register(uninstall_syspath_sleuth)

if __name__ == "__main__":
    go_main_go()

```
