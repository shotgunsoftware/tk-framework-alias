# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

from .socketio.client import AliasSocketIoClient
from .socketio.client_namespace import AliasClientNamespace
from .socketio.client_request_context_manager import ClientRequestContextManager
from .socketio.proxy_wrapper import AliasClientModuleProxyWrapper
from .utils import exceptions
