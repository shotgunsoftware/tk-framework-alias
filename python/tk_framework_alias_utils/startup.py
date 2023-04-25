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
from .utils import version_cmp


PLUGIN_FILENAME = "alias_py"

# NOTE this is the old way to look up the plugin for the current running Alias version.
# Starting from 2023.0 the folder naming should be one-to-one match, e.g. for Alias
# 2023.0 the folder will be "alias2023.0"
ALIAS_PLUGINS = {
    "alias2022.2": {"min_version": "2022.2"},
    "alias2021.3": {"min_version": "2021.3", "max_version": "2022.2"},
    "alias2020.3-alias2021": {"min_version": "2020.3", "max_version": "2021.3"},
    "alias2019-alias2020.2": {"min_version": "2019", "max_version": "2020.3"},
}


def get_plugin_environment(alias_version, alias_exec_path, client_name, client_exe_path, debug="0"):
    """
    Return a dictionary containing the env vars required to launch the plugin.

    :param alias_version: The Alias version that the plugin is running with.
    :type alias_version: str
    :param client_name: The name of the client. This will be used by the plugin to set up a
        communication channel with Alias.
    :type client_name: str
    :param client_exe_path: The path to the python script used by the plugin to start the
        client application.
    :type client_exe_path: str
    :param debug: Set to "1" to run in debug mode, else "0" for non-debug mode.
    :type debug: str

    :return: The plugin environment.
    :rtype: dict
    """

    return {
        "ALIAS_PLUGIN_CLIENT_NAME": client_name,
        "ALIAS_PLUGIN_CLIENT_EXE_PATH": client_exe_path,
        "ALIAS_PLUGIN_CLIENT_PYTHON": sys.executable,
        "ALIAS_PLUGIN_CLIENT_DEBUG": debug,
        "ALIAS_PLUGIN_CLIENT_ALIAS_VERSION": alias_version,
        "ALIAS_PLUGIN_CLIENT_ALIAS_EXECPATH": alias_exec_path,
    }


def ensure_plugin_installed(alias_version):
    """
    Generates plugins.lst file used by alias in the plugins bootstrap process

    :param alias_version: The Alias version string to run the plugin with.
    :typye alias_version: str

    :return: The file path to the .lst file that can be used to auto-load the plugin when
        Alias starts up.
    :rtype: str
    """

    python_major_version = sys.version_info.major
    if python_major_version < 3:
        raise Exception(
            "Python version {}.{}.{} not supported. Python version must >= 3".format(
                sys.version_info.major,
                sys.version_info.minor,
                sys.version_info.micro,
            )
        )

    plugin_dir = os.path.join(os.path.dirname(__file__), "..", "..", "plugin")
    if not os.path.exists(plugin_dir) or not os.path.isdir(plugin_dir):
        return None

    python_folder_name = "python{major}.{minor}".format(
        major=sys.version_info.major,
        minor=sys.version_info.minor,
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

    if not plugin_folder_path:
        return None

    plugin_file_path = os.path.normpath(
        os.path.join(
            plugin_folder_path,
            "{}.plugin".format(PLUGIN_FILENAME),
        )
    )
    if not os.path.exists(plugin_file_path):
        return None

    # Overwrite the lst file with the plugin file path found
    plugins_list_file = os.path.join(tempfile.gettempdir(), "plugins.lst")
    with open(plugins_list_file, "w") as plf:
        plf.write("{}\n".format(plugin_file_path))

    return plugins_list_file
