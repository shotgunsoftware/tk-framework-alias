import os
import sys

PLUGIN_NAME = "com.sg.basic.alias"


def get_alias_plugin_dir():
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

    return os.path.join(app_data, "Autodesk", "Alias", "ShotGrid", "plugin")

def get_plugin_install_directory():
    """Return the file path to the Alias plugin installation for the user."""

    return os.path.join(get_alias_plugin_dir(), PLUGIN_NAME)
