[![Python 3.7 3.9](https://img.shields.io/badge/python-3.7%20%7C%203.9-blue.svg)](https://www.python.org/)
[![Build Status](https://dev.azure.com/shotgun-ecosystem/Toolkit/_apis/build/status/Frameworks/tk-framework-alias?branchName=main)](https://dev.azure.com/shotgun-ecosystem/Toolkit/_build/latest?definitionId=62&branchName=main)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# tk-framework-alias

Toolkit framework for integration with Autodesk Alias.

### Support

- Alias >= 2021
- Windows only

## Development

### <a name="build_toolkit_plugin"></a> Build the Toolkit Plugin

The framework provides the functionality to bootstrap a Toolkit engine (e.g. [tk-alias](https://github.com/shotgunsoftware/tk-alias)) using the the [ToolkitManager](https://github.com/shotgunsoftware/tk-core/blob/master/python/tank/bootstrap/manager.py). A Toolkit Plugin must be created in order to intialize the manager to bootstrap an engine. The framework provides build scripts to generate the plugin bundle; after running the build, it will create the `com.sg.basic.alias` plugin bundle in the `plugin/build` folder. At runtime, the framework will install the plugin bundle to the user's `%APPDATA%` folder ([here](https://github.com/shotgunsoftware/tk-framework-alias/blob/78456698afd090ab2b348503f25c0fa48badf7e8/python/tk_framework_alias_utils/startup.py#L374)), where it can be accessed during the [bootstrap process](https://github.com/shotgunsoftware/tk-framework-alias/blob/init/python/tk_framework_alias_utils/plugin_bootstrap.py).

To build the plugin, see below:

First, set all necessary variables in `dev\env.cmd`. This is what the env file should look like:

```
TARGET_VERSION=1.1.3 # Make sure this matches the tk-framework-alias version you will be releasing

TKCORE_VERSION=0.19.19  # This core version is expected to exist in your bundle cache

PYTHON_EXE=/path/to/python.exe
```

Follow [this link](https://developer.shotgridsoftware.com/7c9867c0/#bundle-cache)
  to find out where your bundle cache is located.

### To build the plugin and install it:

```
cd path/to/tk-framework-alias
cd dev
make build
make install
```

### To remove the latest built plugin bundle:

```
cd path/to/tk-framework-alias
cd dev
make clean
```

### Notes on editing the env file (`env.cmd`)

Changes to the env file (`env.cmd`) will typically not be tracked in git. The information contained in these files is specific to a particular development environment, so tracking changes to that data in git is undesirable.

If you need to make changes to these files, you can use the following commands:

```
git update-index --no-skip-worktree dev/env.mk dev/env.cmd
git add dev\env.*
git commit -m "your message"
git update-index --skip-worktree dev/env.mk dev/env.cmd
```

### <a name="update_python_dist"></a> Update Python Packages Distributable

The framework requires additional python packages to be installed. To ensure the correct packages are found at runtime, the framework will create a distribution folder `dist` at the top-level directory of the repository. The python packages in this folder will be imported at runtime [here](https://github.com/shotgunsoftware/tk-framework-alias/blob/init/python/tk_framework_alias/__init__.py).

To update the packages in the dist folder, run the python script `update_python_packages` from `dev`:

```
cd path/to/tk-framework-alias
cd dev
python update_python_packages.py
```

The framework supports Python 3.7 and 3.9, which means that a package folder must be generated for each version. The package folder that is generated is based on the python version used to run the update script.

## Prep for Release

1. Ensure all python packages are updated in the `dist` folder. See how to update [here](#update_python_dist).
2. Build the Toolkit Plugin `basic.alias` in the `plugin/build` folder. See how to build [here](#build_toolkit_plugin).
