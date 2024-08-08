# Copyright (c) 2024 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

from typing import Optional

class ClientRequestContextManager:
    """
    A context manager to handle executing multiple requests at once.

    The purpose of executing multiple requests at once is to reduce the number
    of socketio requests that are sent to the server. This is useful when
    multiple requests are made in quick succession, and it is more efficient to
    send them all at once.
    """

    def __init__(
        self,
        api_module,
        is_async: Optional[bool] = False
    ):
        """
        Initialize the context manager.

        :param AliasClientModuleProxyWrapper api_module: The Alias api proxy module.
        :param is_async:
        """
        self.__api_module = api_module
        self.__is_async = is_async
        self.result = None

    def __enter__(self):
        """Enter the context manager."""
        self.result = None
        self.__api_module.batch_requests(True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""

        # Execute batched requests and
        self.result = self.__api_module.batch_requests(False, is_async=self.__is_async)
