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
from ... import alias_bridge


class AliasEventsServerNamespace(socketio.Namespace):
    """Namespace for handling Alias Event communication between Alias and ShotGrid."""

    _NAME = "alias-events"

    def __init__(self):
        """Initialize the namespace."""

        super(AliasEventsServerNamespace, self).__init__(self.get_namespace())

    @classmethod
    def get_namespace(cls):
        """Return the namespace string."""
        return f"/{cls._NAME}"

    # Event callback methods for namespace
    # ----------------------------------------------------------------------------------------

    # def on_connect(self, sid, environ):
    #     print(f"{[self.namespace]} connection established", sid)
    #     print("\tenvironment", environ)

    # def on_connect_error(self, data):
    #     print(f"{[self.namespace]} connection error", data)

    # def on_disconnect(self, sid):
    #     print(f"[{self.namespace}] disconnected from server", sid)

    def on_shutdown(self, sid):
        """
        Shutdown the server.

        This event was received from the alias-events client (from the AliasBridge), so the
        AliasBridge will take care of cleaning up the Alias data model. This method just needs
        to forward the shutdown event to all other clients (than the alias-events client).
        """

        # # Destroy the server scope, this will remove any event handlers registered. Do this
        # # before shutting down clients so that their shutdown does not trigger any events.
        # data_model = alias_bridge.AliasBridge().alias_data_model
        # data_model.destroy()

        # Emit event to shutdown all clients in namespaces other than this one.
        self._emit("shutdown")

    def on_restart(self, sid, data):
        """Restart the client."""

        # Shut down all clients
        self.on_shutdown(sid)

        # Restart all clients
        for namespace in self.server.namespace_handlers:
            if namespace != self.namespace:
                alias_bridge.AliasBridge().restart_client(namespace)

    def on_alias_event_callback(self, sid, data):
        """Forward the Alias event callback to the server, to send to all other client namespaces."""

        # Forward alias callback to engine client
        callback_event = data.pop("callback_event")
        self._emit(callback_event, data=data)

    def trigger_event(self, event, sid, *args):
        """Catch all events and dispatch."""

        # First, check if there is a method defined for this specific event.
        event_method_name = f"on_{event}"
        if hasattr(self, event_method_name):
            event_method = getattr(self, event_method_name)
            if callable(event_method):
                return event_method(sid, *args)

    def _emit(self, *args, **kwargs):
        """Emit event to all other namespaces, except this one."""

        for namespace in self.server.namespace_handlers:
            if namespace != self.namespace:
                kwargs["namespace"] = namespace
                self.emit(*args, **kwargs)
