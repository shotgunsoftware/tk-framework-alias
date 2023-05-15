# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

import logging

class WSGIServerLogger(logging.Logger):
    """
    Logger object to pass to the wsgi server.

    NOTE: eventlet.wsgi doc says to use a logging.Logger instance, but this causes an error
    that brings down the wsgi server, and so the clients cannot connect.
    """

    # def info(self, msg, *args, **kwargs):
    #     """Log info message."""

    #     # TODO write this to file?
    #     print(msg)
    #     super(WSGIServerLogger, self).info(msg, *args, **kwargs)

    # def debug(self, msg, *args, **kwargs):
    #     """Log debug message."""

    #     # TODO write this to file?
    #     print(msg)
