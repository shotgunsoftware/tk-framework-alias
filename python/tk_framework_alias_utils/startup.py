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
import traceback
import shutil

from . import environment_utils
from .utils import version_cmp, encrypt_to_str


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
    alias_version,
    alias_exec_path,
    client_name,
    client_exe_path=None,
    python_exe=None,
    pipeline_config_id=None,
    entity_type=None,
    entity_id=None,
    hostname=None,
    port=None,
    debug="0"
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

    env = {
        "ALIAS_PLUGIN_CLIENT_NAME": client_name,
        "ALIAS_PLUGIN_CLIENT_PYTHON": python_exe or sys.executable,
        "ALIAS_PLUGIN_CLIENT_DEBUG": debug,
        "ALIAS_PLUGIN_CLIENT_ALIAS_VERSION": alias_version,
        "ALIAS_PLUGIN_CLIENT_ALIAS_EXECPATH": alias_exec_path,
    }

    if client_exe_path is not None:
        env["ALIAS_PLUGIN_CLIENT_EXECPATH"] = encrypt_to_str(client_exe_path)

    if pipeline_config_id is not None:
        env["ALIAS_PLUGIN_CLIENT_SHOTGRID_PIPELINE_CONFIG_ID"] = str(pipeline_config_id)

    if entity_type is not None:
        env["ALIAS_PLUGIN_CLIENT_SHOTGRID_ENTITY_TYPE"] = str(entity_type)
    
    if entity_id is not None:
        env["ALIAS_PLUGIN_CLIENT_SHOTGRID_ENTITY_ID"] = str(entity_id)

    if hostname is not None:
        env["ALIAS_PLUGIN_CLIENT_SIO_HOSTNAME"] = str(hostname)

    if port is not None:
        env["ALIAS_PLUGIN_CLIENT_SIO_PORT"] = str(port)

    return env


def get_plugin_filename(alias_version):
    """Return the name of the plugin for the Alias version."""

    if version_cmp(alias_version, "2024") >= 0:
        # Alias >= 2024.0
        return "alias_py"

    if version_cmp(alias_version, "2022.2") >= 0:
        # Alias >= 2022.2
        return "shotgrid"

    # Alias < 2022.2
    return "shotgun"

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

    plugin_filename = get_plugin_filename(alias_version)
    plugin_file_path = os.path.normpath(
        os.path.join(
            plugin_folder_path,
            "{}.plugin".format(plugin_filename),
        )
    )

    if not os.path.exists(plugin_file_path):
        return None
    return plugin_file_path


def __ensure_plugin_up_to_date(logger):
    """
    Ensure the basic Alias plugin is up to date.

    Install the plugin to the OS-specific location defined by the environtment utils, if it
    does not exist. If it does exist, check that the installed plugin version is up to date
    with the pre-built plugin in the framework. This requires the framework itself to build
    the plugin bundle and ensure itself reflects the latest version.
    """

    import sgtk
    from sgtk.util.filesystem import ensure_folder_exists

    # Get the directory where the Alias plugin is installed. This directory must exist before
    # attempting to install the plugin
    alias_plugin_dir = environment_utils.get_alias_plugin_dir()
    logger.debug(f"Alias plugin directory: {alias_plugin_dir}")
    if not os.path.exists(alias_plugin_dir):
        logger.debug(f"Alias plugin directory does not exist - creating it.")
        ensure_folder_exists(alias_plugin_dir)

    # Get the path to the pre-built plugin from the framework
    plugin_name = environment_utils.PLUGIN_NAME
    bundled_plugin_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            os.path.pardir,
            "plugin",
            "build",
            plugin_name,
        )
    )
    if not os.path.exists(bundled_plugin_path):
        raise sgtk.TankError(f"Could not find bundled plugin: {bundled_plugin_path}")

    # Ensure that the plugin is installed in the specified directory
    installed_plugin_dir = environment_utils.get_plugin_install_directory()
    if not os.path.exists(installed_plugin_dir):
        logger.debug(f"Installing Alias plugin: {installed_plugin_dir}")
        __install_plugin(bundled_plugin_path, installed_plugin_dir, logger)
        return

    # ---- already installed, check for update

    version_file = f"{plugin_name}.version"

    # Get the version from the installed plugin's build_version.txt file
    installed_version_file_path = os.path.join(installed_plugin_dir, version_file)
    if not os.path.exists(installed_version_file_path):
        logger.debug(f"Could not find installed version file {installed_version_file_path}. Reinstalling")
        __install_plugin(bundled_plugin_path, installed_plugin_dir, logger)
        return

    # ---- found installation, get plugin versions

    # Get the version of the bundled plugin from the framework
    bundled_version_file_path = os.path.abspath(
        os.path.join(
            bundled_plugin_path, version_file
        )
    )
    if not os.path.exists(bundled_version_file_path):
        raise sgtk.TankError(f"Could not find bundled version file: {bundled_version_file_path}")

    # Get the bundled version from the version file
    with open(bundled_version_file_path, "r") as bundled_version_file:
        bundled_version = bundled_version_file.read().strip()
    logger.debug(f"Bundled plugin version: {bundled_version}")

    # Get the installed version from the installed version info file
    logger.debug(f"The installed version file path: {installed_version_file_path}")
    installed_version = None
    with open(installed_version_file_path, "r") as installed_version_file:
        logger.debug("Extracting the version from the installed plugin")
        installed_version = installed_version_file.read().strip()

    if installed_version is None:
        logger.debug("Could not determine version of the installed plugin. Reinstalling")
        __install_plugin(bundled_plugin_path, installed_plugin_dir, logger)
        return

    logger.debug(f"Installed plugin version: {installed_version}")

    # ---- comparing plugin versions

    from sgtk.util.version import is_version_older

    if bundled_version != "dev" and installed_version != "dev":
        if bundled_version == installed_version or is_version_older(
            bundled_version, installed_version
        ):
            # The bundled version is the same or older. or it is a 'dev' build
            # which means always install that one.
            logger.debug("Installed plugin is up to date with the bundled build.")
            return

    # ---- plugin in framework is newer, update the installation

    if bundled_version == "dev":
        logger.debug("Installing the bundled 'dev' version of the plugin.")
    else:
        logger.debug("Bundled plugin is newer than the installed plugin. Updating...")

    __install_plugin(bundled_plugin_path, installed_plugin_dir, logger)


def __install_plugin(plugin_path, install_dir, logger):
    """
    Install the plugin.

    Steps to install:
        1. First, back up the existing installation before removing it, if it exists.
        2. Ensure the bundled plugin to install exists.
        3. Copy the bundled plugin to the installation directory.
        4. If the install fails at any point, restore the back up, if created.

    :param plugin_path: The path to the framework pre-built plugin bundle.
    :type plugin_path: str
    :param install_dir: The plugin installation directory.
    :type install_dir: str
    """

    import sgtk
    from sgtk.util.filesystem import (
        backup_folder,
        copy_folder,
        move_folder,
    )

    # Move the installed plugin bundle to the backup directory
    if os.path.exists(install_dir):
        backup_plugin_dir = tempfile.mkdtemp()
        logger.debug(f"Backing up installed plugin to: {backup_plugin_dir}")
        try:
            backup_folder(install_dir, backup_plugin_dir)
        except Exception:
            shutil.rmtree(backup_plugin_dir)
            raise sgtk.TankError("Unable to create backup during plugin update.")

        # Now remove the installed plugin
        logger.debug("Removing the installed plugin bundle...")
        try:
            shutil.rmtree(install_dir)
        except Exception:
            # Error occured during install - try to restore the backup
            move_folder(backup_plugin_dir, install_dir)
            raise sgtk.TankError("Unable to remove the old plugin during update.")

    logger.debug(f"Installing bundled plugin: {plugin_path} to {install_dir}")

    # Ensure the bundled plugin exists
    if not os.path.exists(plugin_path):
        # Error occured during install - try to restore the backup
        move_folder(backup_plugin_dir, install_dir)
        raise sgtk.TankError(f"Expected plugin bundle does not exist: {plugin_path}")

    # Install the plugin bundle by copying the pre-built plugin to the installation directory
    copy_folder(plugin_path, install_dir)

    # Install was successful, remove the backup
    try:
        logger.debug("Install success. Removing the backed up plugin bundle.")
        shutil.rmtree(backup_plugin_dir)
    except Exception:
        pass


def ensure_plugin_up_to_date(logger):
    """
    Ensure that the Alias plugin is installed and up to date.

    The basic.alias plugin needs to be installed in order to launch the Alias engine. The
    framework will provide a pre-built plugin bundle in the repo plugin/build folder. This
    plugin bundle will be installed for the user at runtime by copying the bundle from the
    framework to the users's Alias AppData folder. The framework will pre-build the plugin
    using the build_extension.py script from the repo dev folder.

    :param logger:
    """

    import sgtk

    if "SHOTGRID_ALIAS_DISABLE_AUTO_INSTALL" in os.environ:
        # Skip plugin installation altogether
        return

    logger.debug("Ensuring Alias plugin is up-to-date...")
    try:
        __ensure_plugin_up_to_date(logger)
    except Exception:
        exc = traceback.format_exc()
        raise sgtk.TankError(
            "There was a problem ensuring the Alias integration plugin "
            "was up-to-date with your toolkit engine. If this is a "
            "recurring issue please contact us via %s. "
            "The specific error message encountered was:\n'%s'."
            % (
                sgtk.support_url,
                exc,
            )
        ) 

def get_plugin_lst(alias_version, python_major_version=None, python_minor_version=None):
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
    lst_file = os.path.join(tempfile.gettempdir(), "alias_plugins.lst")
    with open(lst_file, "w") as fp:
        fp.write("{}\n".format(plugin_file_path))

    return lst_file
