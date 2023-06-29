import os
import sys


TOOLKIT_PLUGIN_NAME = "com.sg.basic.alias"

# The Alias Python API and Alias Plugins are found based on the Alias version that is
# currently running. Defined here is the Alias version grouping:
#
#    < v2020.3              -- distribution folder alias2019-alias2020.2
#   >= v2020.3 & < v2021.3  -- distribution folder alias2020.3-alias2021
#   >= v2021.3 & < v2022.2  -- distribution folder alias2021.3
#   >= v2022.2 & < v2023.0  -- distribution folder alias2022.2
# 
# For Alias >= 2023.0, there will be a dist folder matching the version exactly; e.g.:
#   == v2023.0              -- distribution folder alias2023.0
#   == v2023.1              -- distribution folder alias2023.1
#   etc.
#
# NOTE this Alias version mapping to python api version is deprecated since 2023.0.
# Remove these version mappings as older versions of Alias are dropped from support.
ALIAS_DIST_DIRS = {
    "alias2022.2": {"min_version": "2022.2", "max_version": "2023.0"},
    "alias2021.3": {"min_version": "2021.3", "max_version": "2022.2"},
    "alias2020.3-alias2021": {"min_version": "2020.3", "max_version": "2021.3"},
    "alias2019-alias2020.2": {"min_version": "2019", "max_version": "2020.3"},
}


def get_alias_app_data_dir():
    """
    Get the root directory for the Alias plugin installation.

    This is for Windows only.

    The plugin will be installed inside the user's Alias AppData folder.
    """

    # The plugin install directory is OS-specific
    if sys.platform == "win32":
        app_data = os.getenv("APPDATA")
    else:
        raise Exception("This plugin only runs on Windows.")

    return os.path.join(app_data, "Autodesk", "Alias", "ShotGrid")

def get_alias_plugin_dir():
    """Return the directory containing the Alias plugin installation."""

    return os.path.join(get_alias_app_data_dir(), "plugin")

def get_plugin_install_directory():
    """Return the file path to the Alias plugin installation for the user."""

    return os.path.join(get_alias_plugin_dir(), TOOLKIT_PLUGIN_NAME)

def get_python_directory(major_version, minor_version):
    """
    """

    return os.path.join(
        get_alias_app_data_dir(),
        "Python",
        f"Python{major_version}{minor_version}"
    )

def get_python_install_directory(major_version, minor_version):
    """
    Get the directory to install python for the user.

    If the necessary python version is not found for the current user, the framework can
    install this version for the user.

    :param major_version: The python major version to install for.
    :type major_version: int
    :param minor_version: The python minor version to install for.
    :type minor_version: int

    :return: The file path the python install directory.
    :rtype: str
    """

    return os.path.join(get_python_directory(major_version, minor_version), "install")

def get_python_exe(major_version, minor_version):
    """
    Get the path to the python executable that the Alias Plugin should use.

    It is important that the version of Python that the Alias Plugin uses can install the
    version of PySide2 that matches the Qt version used by Alias.

    :param major_version: The python major version to get the executable for.
    :type major_version: int
    :param minor_version: The python minor version to get the executable for.
    :type minor_version: int

    :return: The file path to the python executable.
    :rtype: str
    """

    return os.path.join(get_python_install_directory(major_version, minor_version), "python.exe")

def get_python_site_packages(major_version, minor_version):
    """
    Get the path to the python site-packages that the Alias Plugin should use.

    It is important that the version of Python that the Alias Plugin uses can install the
    version of PySide2 that matches the Qt version used by Alias.

    :param major_version: The python major version to get the executable for.
    :type major_version: int
    :param minor_version: The python minor version to get the executable for.
    :type minor_version: int

    :return: The file path to the python executable.
    :rtype: str
    """

    return os.path.join(get_python_install_directory(major_version, minor_version), "Lib", "site-packages")

def get_alias_distribution_directory(alias_version, python_major_version, python_minor_version):
    """
    Return the directory containing the Alias distribution files.

    This directory contains the Alias .plugin and Alias Python API .pyd files.

    :param alias_version: The Alias version to look up the directory by.
    :type alias_version: str
    :param python_major_version: The python major version to look up the directory by.
    :type python_major_version: int
    :param python_minor_version: The python minor verison to look up the directory by.
    :type python_minor_version: int

    :return: The file path to the Alias distribution directory.
    :rtype: str
    """

    from .utils import version_cmp

    python_version = "{major}.{minor}".format(
        major=python_major_version,
        minor=python_minor_version,
    )
    python_folder_name = "python{}".format(python_version)

    # Determine the name of the folder containing the files to import according to the version
    # of Alias

    # First try to get the folder directly matching the running version of Alias
    dist_folder_name = f"alias{alias_version}"
    base_folder_path = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            os.pardir,
            os.pardir,
            "dist",
            "Alias",
            python_folder_name,
        )
    )
    dist_folder_path = os.path.join(base_folder_path, dist_folder_name)

    # Return right away if the path exists
    if os.path.exists(dist_folder_path):
        return dist_folder_path

    # This is an older build, look up based on Alias version grouping.
    for folder_name in ALIAS_DIST_DIRS:
        min_version = ALIAS_DIST_DIRS[folder_name].get("min_version")
        if min_version and version_cmp(alias_version, min_version) < 0:
            continue
        max_version = ALIAS_DIST_DIRS[folder_name].get("max_version")
        if max_version and version_cmp(alias_version, max_version) >= 0:
            continue
        # Found the folder name, now create the full path
        return os.path.join(base_folder_path, folder_name)

    # Failed to find the Alias distribution folder. 
    return None

def get_alias_api_cache_file_path(filename, alias_version, python_version):
    """Return the file path the cached api .json file."""

    return os.path.join(
        get_alias_app_data_dir(),
        "api",
        f"{filename}{alias_version}_py{python_version}.json",
    )

def get_python_embed_package_name(major_version, minor_version):
    """Return the name of the embeddable python package."""

    return f"python-{major_version}.{minor_version}-embed-amd64"

def get_framework_python_path():
    """Return the absolute file path to the root python directory."""

    # Relative to this file location
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            os.pardir,
        )
    )
