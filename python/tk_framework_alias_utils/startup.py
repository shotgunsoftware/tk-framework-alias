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

    return {
        "ALIAS_PLUGIN_CLIENT_NAME": client_name,
        "ALIAS_PLUGIN_CLIENT_EXECPATH": "" if client_exe_path is None else encrypt_to_str(client_exe_path),
        "ALIAS_PLUGIN_CLIENT_PYTHON": python_exe or sys.executable,
        "ALIAS_PLUGIN_CLIENT_DEBUG": debug,
        "ALIAS_PLUGIN_CLIENT_ALIAS_VERSION": alias_version,
        "ALIAS_PLUGIN_CLIENT_ALIAS_EXECPATH": alias_exec_path,
        "ALIAS_PLUGIN_CLIENT_SHOTGRID_PIPELINE_CONFIG_ID": "" if pipeline_config_id is None else str(pipeline_config_id),
        "ALIAS_PLUGIN_CLIENT_SHOTGRID_ENTITY_TYPE": "" if entity_type is None else entity_type,
        "ALIAS_PLUGIN_CLIENT_SHOTGRID_ENTITY_ID": "" if entity_id is None else str(entity_id),
    }


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


def __ensure_extension_up_to_date(logger):
    """
    Ensure the basic Alias plugin is installed in the OS-specific location
    and that it matches the extension bundled with the installed engine.
    """

    import sgtk
    from sgtk.util.filesystem import ensure_folder_exists

    extension_name = environment_utils.EXTENSION_NAME

    # the Alias plugin install directory. This is where the plugin is stored.
    alias_plugin_dir = environment_utils.get_alias_plugin_dir()
    logger.debug(f"Alias plugin dir: {alias_plugin_dir}")

    installed_ext_dir = environment_utils.get_plugin_install_directory()

    # make sure the directory exists. create it if not.
    if not os.path.exists(alias_plugin_dir):
        logger.debug("Plugin folder does not exist. Creating it.")
        ensure_folder_exists(alias_plugin_dir)

    # get the path to the installed engine's .zxp file.
    bundled_ext_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            os.path.pardir,
            "plugin",
            "build",
            # "%s.zxp" % (extension_name,),
            extension_name,
        )
    )

    if not os.path.exists(bundled_ext_path):
        raise sgtk.TankError(
            "Could not find bundled extension. Expected: '%s'" % (bundled_ext_path,)
        )

    # now get the version of the bundled extension
    version_file = "%s.version" % (extension_name,)

    bundled_version_file_path = os.path.abspath(
        os.path.join(
            bundled_ext_path, version_file
        )
    )

    if not os.path.exists(bundled_version_file_path):
        raise sgtk.TankError(
            "Could not find bundled version file. Expected: '%s'"
            % (bundled_version_file_path,)
        )

    # get the bundled version from the version file
    with open(bundled_version_file_path, "r") as bundled_version_file:
        bundled_version = bundled_version_file.read().strip()

    # check to see if the extension is installed in the CEP extensions directory
    # if not installed, install it
    if not os.path.exists(installed_ext_dir):
        logger.debug("Extension not installed. Installing it!")
        __install_extension(bundled_ext_path, installed_ext_dir, logger)
        return

    # ---- already installed, check for udpate

    logger.debug("Bundled extension's version is: %s" % (bundled_version,))

    # get the version from the installed extension's build_version.txt file
    installed_version_file_path = os.path.join(installed_ext_dir, version_file)

    logger.debug(
        "The installed version file path is: %s" % (installed_version_file_path,)
    )

    if not os.path.exists(installed_version_file_path):
        logger.debug(
            "Could not find installed version file '%s'. Reinstalling"
            % (installed_version_file_path,)
        )
        __install_extension(bundled_ext_path, installed_ext_dir, logger)
        return

    # the version of the installed extension
    installed_version = None

    # get the installed version from the installed version info file
    with open(installed_version_file_path, "r") as installed_version_file:
        logger.debug("Extracting the version from the installed extension.")
        installed_version = installed_version_file.read().strip()

    if installed_version is None:
        logger.debug(
            "Could not determine version for the installed extension. Reinstalling"
        )
        __install_extension(bundled_ext_path, installed_ext_dir, logger)
        return

    logger.debug("Installed extension's version is: %s" % (installed_version,))

    from sgtk.util.version import is_version_older

    if bundled_version != "dev" and installed_version != "dev":
        if bundled_version == installed_version or is_version_older(
            bundled_version, installed_version
        ):

            # the bundled version is the same or older. or it is a 'dev' build
            # which means always install that one.
            logger.debug(
                "Installed extension is equal to or newer than the bundled "
                "build. Nothing to do!"
            )
            return

    # ---- extension in engine is newer. update!

    if bundled_version == "dev":
        logger.debug("Installing the bundled 'dev' version of the extension.")
    else:
        logger.debug(
            (
                "Bundled extension build is newer than the installed extension "
                "build! Updating..."
            )
        )

    # install the bundle
    __install_extension(bundled_ext_path, installed_ext_dir, logger)


def __install_extension(ext_path, dest_dir, logger):
    """
    Installs the supplied extension path by unzipping it directly into the
    supplied destination directory.

    :param ext_path: The path to the .zxp extension.
    :param dest_dir: The CEP extension's destination
    :return:
    """

    import sgtk
    from sgtk.util.filesystem import (
        backup_folder,
        copy_folder,
        move_folder,
    )

    # move the installed extension to the backup directory
    if os.path.exists(dest_dir):
        backup_ext_dir = tempfile.mkdtemp()
        logger.debug("Backing up the installed extension to: %s" % (backup_ext_dir,))
        try:
            backup_folder(dest_dir, backup_ext_dir)
        except Exception:
            shutil.rmtree(backup_ext_dir)
            raise sgtk.TankError("Unable to create backup during extension update.")

        # now remove the installed extension
        logger.debug("Removing the installed extension directory...")
        try:
            shutil.rmtree(dest_dir)
        except Exception:
            # try to restore the backup
            move_folder(backup_ext_dir, dest_dir)
            raise sgtk.TankError("Unable to remove the old extension during update.")

    logger.debug("Installing bundled extension: '%s' to '%s'" % (ext_path, dest_dir))

    # make sure the bundled extension exists
    if not os.path.exists(ext_path):
        # retrieve backup before aborting install
        move_folder(backup_ext_dir, dest_dir)
        raise sgtk.TankError(
            "Expected CEP extension does not exist. Looking for %s" % (ext_path,)
        )

    # copy the plugin bundle to the destination dir
    copy_folder(ext_path, dest_dir)

    # if we're here, the install was successful. remove the backup
    try:
        logger.debug("Install success. Removing the backed up extension.")
        shutil.rmtree(backup_ext_dir)
    except Exception:
        # can't remove temp dir. no biggie.
        pass


def ensure_plugin_up_to_date(logger, alias_version, python_major_version=None, python_minor_version=None):
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

    """
    Carry out the necessary operations needed in order for the
    Adobe extension to be recognized.

    This inlcudes copying the extension from the engine location
    to a OS-specific location.
    """

    import sgtk

    # the basic plugin needs to be installed in order to launch the Alias
    # engine. we need to make sure the plugin is installed and up-to-date.
    # will only run if SHOTGRID_ALIAS_DISABLE_AUTO_INSTALL is not set.
    if "SHOTGRID_ALIAS_DISABLE_AUTO_INSTALL" not in os.environ:
        logger.debug("Ensuring Alias plugin is up-to-date...")
        try:
            __ensure_extension_up_to_date(logger)
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

    # 
    # Creating the .lst file for the Alias plugin
    # 
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
