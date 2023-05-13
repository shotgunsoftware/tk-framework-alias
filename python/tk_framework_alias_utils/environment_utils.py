import os


EXTENSION_NAME = "com.sg.basic.alias"


def get_alias_plugin_dir():
    """Get the file path to install the Alias plugin."""

    from sgtk import util

    # The plugin install directory is OS-specific
    if util.is_windows():
        app_data = os.getenv("APPDATA")
    else:
        raise Exception("This engine only runs on Windows.")

    return os.path.join(app_data, "Autodesk", "Alias", "ShotGrid", "plugin")

def get_plugin_install_directory():
    """
    """

    return os.path.join(get_alias_plugin_dir(), EXTENSION_NAME)
