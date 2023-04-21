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
from .events_namespace import AliasEventsServerNamespace


class AliasEventsClientNamespace(socketio.ClientNamespace):
    """Namespace for the Alias Events client."""

    def __init__(self):
        """Initialize the namespace."""

        namespace = AliasEventsServerNamespace.get_namespace()
        super(AliasEventsClientNamespace, self).__init__(namespace)
