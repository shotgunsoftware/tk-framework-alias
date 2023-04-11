# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import socketio


class AliasServer(socketio.Server):
    """Custom socketio server for Alias."""

    def __init__(self, plugin_version, alias_version, python_version, *args, **kwargs):
        """Initialize"""

        super(AliasServer, self).__init__(*args, **kwargs)

    #     self.__plugin_version = plugin_version
    #     self.__alias_version = alias_version
    #     self.__python_version = python_version
    
    # @property
    # def plugin_version(self):
    #     """Get the Alias Plugin version that created this bridge."""
    #     return self.__plugin_version

    # @property
    # def alias_version(self):
    #     """
    #     Get the Alias version that this bridge should be running with.

    #     This is the Alias version that the Alias Plugin was compiled with.
    #     """
    #     return self.__alias_version

    # @property
    # def python_version(self):
    #     """
    #     Get the Python version that this bridge should be running with.

    #     This is the Python version that the Alias Plugin was compiled with.
    #     """
    #     return self.__python_version
