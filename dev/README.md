# Development

### Support

- Windows

The framework has a couple pre-release steps:

1. Include a pre-built [Toolkit Plugin](#build_toolkit_plugin)
2. Include any necessary [embeddable Python packages](#embed_py_package)

## <a name="build_toolkit_plugin"></a> Build the Toolkit Plugin

The framework provides the functionality to bootstrap a Toolkit engine (e.g. [tk-alias](https://github.com/shotgunsoftware/tk-alias)) using the the [ToolkitManager](https://github.com/shotgunsoftware/tk-core/blob/master/python/tank/bootstrap/manager.py). A Toolkit Plugin must be created in order to intialize the manager to bootstrap an engine. The framework provides build scripts to generate the plugin bundle; after running the build, it will create the `com.sg.basic.alias` plugin bundle in the `dist/Toolkit/plugin` folder. At runtime, the framework start up utils will install the plugin bundle to the user's `%APPDATA%` folder, where it can be accessed during the [bootstrap process](https://github.com/shotgunsoftware/tk-framework-alias/blob/init/python/tk_framework_alias_utils/plugin_bootstrap.py).

The following files are provided to build the plugin:

- env.cmd
- make.bat
- build_plugin.py

The actual plugin is built from the file `plugin/Toolkit/basic/info.yml`. The `info.yml` defines the Toolkit Plugin.

Before exeuting the build scripts, set all necessary variables in `dev\env.cmd`. These environment variables will be set by calling `env.cmd` from the `make.bat` file. This is what the env file should look like:

```
TARGET_VERSION=1.1.3 # Make sure this matches the tk-framework-alias version you will be releasing

TKCORE_VERSION=0.19.19  # This core version is expected to exist in your bundle cache

PYTHON_EXE=/path/to/python.exe
```

Follow [this link](https://developer.shotgridsoftware.com/7c9867c0/#bundle-cache) to find out where your bundle cache is located.

### Build

Run the build to create the plugin bunlde in the `dist/Toolkit/plugin` folder. This is all that is needed to prep the plugin for release with the framework.

```
cd path/to/tk-framework-alias
cd dev
make build
```

### Install

Optionally, you can install the plugin immediately to your `%APPDATA%` folder. This install step will be done at run time in the start up utils, if it does not exist.

```
cd path/to/tk-framework-alias
cd dev
make build
make install
```

### Remove plugin build

```
cd path/to/tk-framework-alias
cd dev
make clean
```

## <a name="embed_py_package"></a>Embeddable Python Package

The `get-pip.py` script is included for convenience to set up the embeddable Python packages in `dist` (see [pip installation](https://pip.pypa.io/en/stable/installation/)) The base embeddable Python packages do not come with pip, so this script can be used to make pip available to the embeddable Python, which can then be used to install any additional required Python packages. See [dist](https://github.com/shotgunsoftware/tk-framework-alias/blob/initial/dist/README.md) for more details on how to set up the embeddable Python package.
