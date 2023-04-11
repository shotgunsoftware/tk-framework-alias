# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from .alias_bridge import AliasBridge
from .socket_io.namespaces.alias_server_namespace import AliasServerNamespace


class AliasBridgeConnector():
    """Manage connecting a specific client to the AliasBridge."""

    def __init__(self, client_version, alias_version, python_version, namespace, client_exe_path):
        """Initialize"""

        self.__client_version = client_version
        self.__alias_version = alias_version
        self.__python_version = python_version
        self.__client_exe_path = client_exe_path
        self.__namespace = namespace
        self.__namespace_handler = AliasServerNamespace(namespace, self.__client_exe_path)

        AliasBridge().register_connector(self, self.__namespace_handler)


    @property
    def namespace(self):
        """Get the namespace string this connector has registered to the Alias bridge server."""
        return self.__namespace

    def start_server(self, host=None, port=None, max_retries=None):
        """Convenience function to start the Alias Bridge."""

        return AliasBridge().start(host, port, max_retries)

    def stop_server(self):
        """Convenience function to stop the Alias Bridge server."""

        return AliasBridge().stop()

    def info(self):
        """Return a dictionary of information about this connector."""

        return {
            "plugin": {
                "version": self.__client_version,
                "alias_version": self.__alias_version,
                "python_version": self.__python_version,
            },
        }

    def bootstrap_client(self):
        """Bootstrap the Alias client."""

        return AliasBridge().bootstrap_client(
            self.__client_exe_path, self.__namespace_handler.namespace
        )
