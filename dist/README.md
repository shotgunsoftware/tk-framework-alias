# Distributed Files

The framework includes distributed files:

- Alias
    - Alias Plugin for supported Alias version
    - Alias Python API modules
- Toolkit
    - Pre-built [Toolkit Plugin](#toolkit-plugin) bundle
- Python
    - Python37
        - A minimal [embeddable package](#embeddable-python-package) for Python 3.7
        - [Required python packages](#required-python-packages) running the framework with 3.7
    - Python39
        - [Required python packages](#required-python-packages) running the framework with 3.9
    - Python310
        - [Required python packages](#required-python-packages) running the framework with 3.10

The Alias distributed files are maintained by the Flow Production Tracking Automotive Team.

## Toolkit Plugin

The pre-built Toolkit Plugin bundle is generated by running scripts for `dev`. See [dev](https://github.com/shotgunsoftware/tk-framework-alias/tree/main/dev) for more details.

## Embeddable Python Package

The embeddable Python packages are included to ensure a compatible version of Python (and Qt) are available to run the framework with Alias.

For example, Alias 2024.0 uses Qt version 5.15.0, which means the framework must use the matching version of PySide2 5.15.0. PySide 5.15.0 requires Python version < 3.9, so in the event that the user is running with Python >= 3.9, the framework will install the embeddable Python 3.7 package to the user's local `%APPDATA%` folder, and use that version of Python with the framework (instead of the version of Python currently running).

### How to create an embeddable package

1. Download the base embeddable package for the desired Python version from [here](https://www.python.org/ftp/python/).
2. After downloading, unzip the package.
3. Downlad the get-pip.py script [here](https://pip.pypa.io/en/stable/installation/) to the dev directory.
3. Add pip to the python package by running:

```
dist/Python37/python-3.7-embed-amd64/python.exe dev/get-pip.py
```

This will add the `Lib` and `Scripts` folder to the base package.

4. Edit the file `python{major_version}{minor_version}._pth` to uncomment the `import site` line, such that the file content appears as:

```
python37.zip
.

# Uncomment to run site.main() automatically
import site
```

This allows python to find and execute pip:
```
dist/Python37/python-3.7-embed-amd64/python.exe -m pip
```

5. If necessary update the `requirements.txt` at the Python version root level folder to include any addition python package to install. The requirements should look similar to:

```
eventlet
PySide2==5.15.0
python-socketio
websocket-client
requests
```

6. Zip up the package again. Make sure that when unzipping the package, the `python.exe` file is in the root folder (e.g. make sure an intermediate folder is not added on zip).

At run time, the framework's start up utils will check if the current version of Python is compatible with the framework. If it is not, the framework will install the embeddable package to the user's `%APPDATA%` folder by unzipping `python-3.7-embed-amd64.zip` to `%APPDATA%/Autodesk/Alias/ShotGrid/Python/Python37/install`. The additional packages will be installed using pip and the requiements.txt to `Lib/site-packages`. Regardless of which version of Python is being used, these installed site-packages will be imported by the framework [here](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/python/tk_framework_alias/__init__.py), to ensure the correct package versions are used.

If the embeddable package needs to be updated, for example, to add more site-packages, remember to update the `embed_version.txt` file to bump the version. This version is checked to see if the installed embedded package needs to be updated on the user's local disk.

## Required Python Packages

Additional Python packages are required to run the framework that Flow Production Tracking Toolkit does not ship with. These packages are added to the Python system path at run time [here](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/python/tk_framework_alias/__init__.py#L11-L20). By including the packages in the path, these modules must be made available by either:

1. Dynamically install packages from a requirements file to the user's AppData folder using pip install.
2. Pre-install packages to the framework.

While option (1) is easier for code maintenance and to ensure the latest packages are installed, the down side is that it requires the user environment to allow pip installations. Option (2) guarantees that the packages are available to the framework, though it is at the cost of developer maintenance. Each time there is a change to the required pacakges, the packages need to be pre-installed and updated in the `dist` folder.

Since pip is not guaranteed to work, option (2) has been chosen for the current implementation (though the dynamic pip install code has been left in the start up utils, in case for future use).

### Update the required packages

The pre-built and installed packages are generated by running the `update_python_packages.py` in `dev`. See the [here](https://github.com/shotgunsoftware/tk-framework-alias/tree/main/dev/README.md) for more details.
