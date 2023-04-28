# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import socketio

from ...api import alias_api

from .events_namespace import AliasEventsServerNamespace
from ..api_request import AliasApiRequestWrapper
from ... import alias_bridge
from ...utils.invoker import execute_in_main_thread
from ...utils.exceptions import (
    AliasApiRequestException,
    AliasApiRequestNotSupported,
    AliasApiPostProcessRequestError,
    AliasApiRequestError,
)


class AliasServerNamespace(socketio.Namespace):
    """Namespace for handling communication to Alias."""

    _NAME = "alias"

    def __init__(self, sub_namespace=None):
        """Initialize the namespace."""

        namespace = f"/{self._NAME}"
        if sub_namespace:
            namespace = f"{namespace}-{sub_namespace}"

        super(AliasServerNamespace, self).__init__(namespace)

    @classmethod
    def get_namespace(cls):
        """Return the namespace string."""
        return f"/{cls._NAME}"

    # Event callback methods for namespace
    # ----------------------------------------------------------------------------------------

    def on_connect(self, sid, environ):
        """The connect event callback."""

        with self.session(sid) as session:
            session["SERVER_NAME"] = environ.get("SERVER_NAME")
            session["SERVER_PORT"] = environ.get("SERVER_PORT")

    def on_connect_error(self, data):
        """The connect error event callback."""

        # TODO log message
        print(f"{[self.namespace]} connection error", data)

    def on_disconnect(self, sid):
        """The disconnect event callback."""

        # TODO log message
        print(f"[{self.namespace}] disconnected from server", sid)

    def on_restart(self, sid):
        """Restart the client."""

        # First destroy the scope
        data_model = alias_bridge.AliasBridge().alias_data_model
        data_model.destroy()

        # Emit event to shutdown all clients.
        # We can't wait because the client is going to disconnect - should the server disconnect it?
        self.emit("shutdown", namespace=self.namespace)

        alias_bridge.AliasBridge().restart_client(self.namespace)

    def on_get_alias_api(self, sid):
        """Get the global attributes for the Alias Python API."""

        return alias_api

    def on_add_server_menu(self, sid, menu):
        """The Alias plugin menu was created. Add server menu actions to it."""

        @execute_in_main_thread
        def add_menu_action(menu, data):
            submenu = menu.add_menu("Server Menu")
            alias_sio = alias_bridge.AliasBridge().alias_events_client_sio

            # Command callback needs to be sent to the events namespace because...?
            menu.add_command(
                "Restart Client...",
                lambda: alias_sio.emit(
                    "restart",
                    data=data,
                    namespace=AliasEventsServerNamespace.get_namespace(),
                ),
                parent=submenu,
            )

        with self.session(sid) as session:
            data = {
                "hostname": session.get("SERVER_NAME"),
                "port": session.get("SERVER_PORT"),
                "namespace": self.namespace,
            }
            add_menu_action(menu, data)

    def on_get_alias_api_info(self, sid):
        """Return the Alias Python API module info."""

        api_filepath = alias_api.__file__
        last_modified = os.stat(api_filepath).st_mtime

        return {
            "version": alias_api.__version__,
            "alias_version": alias_api.__alias_version__,
            "python_version": alias_api.__python_version__,
            "file_path": api_filepath,
            "last_modified": last_modified,
        }

    def on_alias_api_last_modified(self, sid):
        """Return the last modified datetime of the Alias Python API module."""

        api_filepath = alias_api.__file__
        last_modified = os.stat(api_filepath).st_mtime
        return last_modified

    def on_server_info(self, sid):
        """Return the server information."""

        api_info = self.on_get_alias_api_info(sid)
        client_info = (
            alias_bridge.AliasBridge()
            .get_client_by_namespace(self.namespace)
            .get("info")
        )
        return {
            "api": api_info,
            "client": client_info,
        }

    def trigger_event(self, event, sid, *args):
        """Catch all events and dispatch."""

        # First, check if there is a method defined for this specific event.
        event_method_name = f"on_{event}"
        if hasattr(self, event_method_name):
            event_method = getattr(self, event_method_name)
            if callable(event_method):
                return event_method(sid, *args)

        else:
            # Make the Alias Python API call
            data = args[0] if args else None
            result = self._execute_request(event, data)

            # Do any post processing after the request has been made.
            self._post_process_request(event, data, result)

            return result

    @execute_in_main_thread
    def _execute_request(self, request_name, request):
        """Execute the Alias Python API request."""

        if not isinstance(request, AliasApiRequestWrapper):
            # Do not raise, just return the exception to be sent back to the client(s)
            return AliasApiRequestNotSupported(f"Request not supported: {request}")

        try:
            result = request.execute(request_name)
            return result

        except AliasApiRequestException as api_error:
            # Report api specific exceptions.
            return api_error

        except Exception as general_error:
            # Report a general error that occurred trying to execute the api request.
            return AliasApiRequestError(general_error)

    def _post_process_request(self, event, data, result):
        """Do any post processing to the result."""

        try:
            if event == "add_message_handler":
                alias_event_id = data.func_args[0]
                event_callback_id = result[1]
                data_model = alias_bridge.AliasBridge().alias_data_model
                data_model.register_event(alias_event_id, event_callback_id)

            elif event == "remove_message_handler":
                alias_event_id = data.func_args[0]
                event_callback_id = data.func_args[1]
                data_model = alias_bridge.AliasBridge().alias_data_model
                data_model.unregister_event(alias_event_id, event_callback_id)

        except Exception as post_process_error:
            return AliasApiPostProcessRequestError(post_process_error)
