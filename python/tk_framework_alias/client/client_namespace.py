# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import socketio


class AliasClientNamespace(socketio.ClientNamespace):
    """Namespace for communication with Alias."""

    def on_disconnect(self):
        """Disconnect event"""

        self.client.cleanup()

    def on_shutdown(self):
        """Shutdown event received from server."""

        try:
            self.disconnect()
        except:
            # Do nothing, the server may have already dropped.
            pass

    def trigger_event(self, event, *args):
        """Catch all server events"""

        event_method_name = f"on_{event}"
        if hasattr(self, event_method_name):
            event_method = getattr(self, event_method_name)
            if callable(event_method):
                return event_method(*args)

        # No specific event found, check if this is a callback from Alias.
        callback_function = self.client.get_callback(event)
        if callback_function:
            # TODO logging here
            print(f"ALIAS CALLBACK {event}")
            result = self._handle_callback(callback_function, *args)
            print(f"\tcallback result {result}")
            return result

    def _handle_callback(self, callback_func, data=None):
        """Handle callback from the Alias Python Api that was forwarded from the socket."""

        data = data or {}
        args = data.get("args", [])
        kwargs = data.get("kwargs", {})
        return callback_func(*args, **kwargs)
