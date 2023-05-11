# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sys
import tempfile
from .utils import version_cmp, encrypt_to_str


# Name of the compiled plugin file, e.g. alias_py.plugin
PLUGIN_FILENAME = "alias_py"
PLUGIN_FILENAMES = {
    "alias2024.0": "alias_py",
    "2023.1": "shotgrid",
    "2023.0": "shotgrid",
    "2022.2": "shotgrid",
}

# NOTE this is the old way to look up the plugin for the current running Alias version.
# Starting from 2023.0 the folder naming should be one-to-one match, e.g. for Alias
# 2023.0 the folder will be "alias2023.0"
ALIAS_PLUGINS = {
    "alias2022.2": {"min_version": "2022.2"},
    "alias2021.3": {"min_version": "2021.3", "max_version": "2022.2"},
    "alias2020.3-alias2021": {"min_version": "2020.3", "max_version": "2021.3"},
    "alias2019-alias2020.2": {"min_version": "2019", "max_version": "2020.3"},
}


def get_plugin_environment(
    alias_version, alias_exec_path, client_name, client_exe_path, python_exe=None, debug="0"
):
    """
    Return a dictionary containing the env vars required to launch the plugin.

    Environment:
        ALIAS_PLUGIN_CLIENT_NAME - name used to uniquely identify the Alias client app
        ALIAS_PLUGIN_CLIENT_EXECPATH - path to python script to start the client app
        ALIAS_PLUGIN_CLIENT_PYTHON - the path to the python exe to run the python script
        ALIAS_PLUGIN_CLIENT_DEBUG - indicate debug mode on or off
        ALIAS_PLUGIN_CLIENT_ALIAS_VERSION - the Alias version the client is requesting
        ALIAS_PLUGIN_CLIENT_ALIAS_EXECPATH - the path to the Alias exe

    :param alias_version: The Alias version that the plugin is running with.
    :type alias_version: str
    :param client_name: The name of the client. This will be used by the plugin to set up a
        communication channel with Alias.
    :type client_name: str
    :param client_exe_path: The path to the python script used by the plugin to start the
        client application.
    :type client_exe_path: str
    :param python_exe: Option to specify a python.exe to run the client app with. Defaults
        to the sys.executable
    :type python_exe: str
    :param debug: Set to "1" to run in debug mode, else "0" for non-debug mode.
    :type debug: str

    :return: The plugin environment.
    :rtype: dict
    """

    return {
        "ALIAS_PLUGIN_CLIENT_NAME": client_name,
        "ALIAS_PLUGIN_CLIENT_EXECPATH": encrypt_to_str(client_exe_path),
        "ALIAS_PLUGIN_CLIENT_PYTHON": python_exe or sys.executable,
        "ALIAS_PLUGIN_CLIENT_DEBUG": debug,
        "ALIAS_PLUGIN_CLIENT_ALIAS_VERSION": alias_version,
        "ALIAS_PLUGIN_CLIENT_ALIAS_EXECPATH": alias_exec_path,
    }


def get_plugin_dir():
    """Return the file path to the plugin directory."""

    plugin_dir = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "plugin"
        )
    )

    if not os.path.exists(plugin_dir) or not os.path.isdir(plugin_dir):
        return None
    return plugin_dir

def get_plugin_file_path(alias_version, python_major_version, python_minor_version):
    """
    Get the file path to the plugin file given the python and alias version.

    :param alias_version: Find the plugin for this Alias version
    :type alias_version: str
    :param python_major_version: Find the plugin for this python major version.
    :type python_major_version: int
    :param python_minor_version: Find the plugin for this python minor version.
    :type python_minor_version: int

    :return: The file path to the plugin file.
    :rtype: str
    """

    # Get the root directory for the plugins
    plugin_dir = get_plugin_dir()

    # Get the name of the folder based on the python version
    python_folder_name = "python{major}.{minor}".format(
        major=python_major_version,
        minor=python_minor_version,
    )

    # First try to get the plugin folder directly matching the running version of Alias,
    # and the exact running python version
    plugin_folder_name = "alias{version}".format(version=alias_version)
    plugin_folder_path = os.path.normpath(
        os.path.join(
            plugin_dir,
            python_folder_name,
            plugin_folder_name,
        )
    )

    if not os.path.exists(plugin_folder_path):
        # Folder not found, try the plugin mapping to Alias version
        plugin_folder_path = None
        for plugin_folder_name in ALIAS_PLUGINS:
            min_version = ALIAS_PLUGINS[plugin_folder_name].get("min_version")
            max_version = ALIAS_PLUGINS[plugin_folder_name].get("max_version")

            if min_version and version_cmp(alias_version, min_version) < 0:
                continue

            if max_version and version_cmp(alias_version, max_version) >= 0:
                continue

            # Found the folder name, try to get the full path now.
            plugin_folder_path = os.path.normpath(
                os.path.join(
                    plugin_dir,
                    python_folder_name,
                    plugin_folder_name,
                )
            )
            break
        else:
            return None

    plugin_filename = PLUGIN_FILENAMES.get(alias_version, "alias_py")
    plugin_file_path = os.path.normpath(
        os.path.join(
            plugin_folder_path,
            "{}.plugin".format(plugin_filename),
        )
    )

    if not os.path.exists(plugin_file_path):
        return None
    return plugin_file_path

def ensure_plugin_installed(alias_version, python_major_version=None, python_minor_version=None):
    """
    Create the .lst file used to launch the alias_py plugin on Alias start up.

    The .lst file can be used, for example:

        Alias.exe -a as -P "path\\to\\plugin.lst"

    The .lst file will be created in a temp directory.

    :param alias_version: The Alias version string to run the plugin with.
    :type alias_version: str
    :param python_major_version: Option to specify the python major version to install the
        plugin for. Defaults to use the python version defined by sys.version_info.
    :type python_major_version: int
    :param python_minor_version: Option to specify the python minor version to install the
        plugin for. Defaults to use the python version defined by sys.version_info.
    :type python_minor_version: int

    :return: The file path to the .lst file.
    :rtype: str
    """

    if python_major_version is None:
        python_major_version = sys.version_info.major
    if python_minor_version is None:
        python_minor_version = sys.version_info.minor

    # Get the path to the .plugin file
    plugin_file_path = get_plugin_file_path(alias_version, python_major_version, python_minor_version)
    if plugin_file_path is None:
        raise Exception(f"Failed to find plugin for Alias {alias_version} Python {python_major_version}.{python_minor_version}")

    # Create or overwrite the lst file with the plugin file path found
    lst_file = os.path.join(tempfile.gettempdir(), "plugins.lst")
    with open(lst_file, "w") as fp:
        fp.write("{}\n".format(plugin_file_path))

    return lst_file
