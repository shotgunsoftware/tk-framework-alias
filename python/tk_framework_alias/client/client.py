# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

from functools import wraps
import json
import os
import socketio
import threading
import tempfile

from .client_json import AliasClientJSON

# TODO move this decorator somewhere else..
def check_result(func):
    """Check the result returned by the server."""

    @wraps(func)
    def wrapper(client, *args, **kwargs):
        try:
            result = func(client, *args, **kwargs)
        except Exception as error:
            result = error
        
        if isinstance(result, Exception):
            return client._handle_server_error(result)
        return result
    
    return wrapper
        

class AliasSocketIoClient(socketio.Client):
    """A custom socketio client to communicate with Alias."""

    def __init__(self, *args, **kwargs):
        """Initialize the client."""

        if "json" not in kwargs:
            # Default to the Alias client JSON if not provided.
            self.__json = AliasClientJSON
            kwargs["json"] = self.__json
        else:
            self.__json = None

        super(AliasSocketIoClient, self).__init__(*args, **kwargs)

        self.__hostname = None
        self.__port = None
        self.__timeout = kwargs.get("timeout", 20)
        self.__callbacks = {}
        self.__callback_lock = threading.Lock()
        self.__message_queue_lock = threading.Lock()
        self.__namespaces = []
        self._default_namespace = None


    # -------------------------------------------------------------------------------------------------------
    # Properties

    @property
    def hostname(self):
        """Get the hostname that this client is connected to."""
        return self.__hostname

    @property
    def port(self):
        """Get the port number that this client is connected to."""
        return self.__port

    @property
    def json(self):
        """Get the JSON module used to handle serializing data with the server."""
        return self.__json


    # -------------------------------------------------------------------------------------------------------
    # Public methods

    def get_json_encoder(self):
        """Get the JSON encoder class used to handle serializing data with the server."""

        if self.__json is AliasClientJSON:
            return self.__json.encoder_class()
        return None

    def get_json_decoder(self):
        """Get the JSON decoder class used to handle serializing data with the server."""

        if self.__json is AliasClientJSON:
            return self.__json.decoder_class()
        return None

    def add_namespace(self, namespace_handler):
        """Register a namespace and add it to the list of namespaces used for connection."""

        self.__namespaces.append(namespace_handler.namespace)
        self.register_namespace(namespace_handler)

    def start(self, hostname, port):
        """Start the socketio by connecting to the server."""

        # TODO secure https
        self.__hostname = hostname
        self.__port = port

        url = f"http://{self.__hostname}:{self.__port}"

        self.connect(
            url,
            namespaces=self.__namespaces,
            wait_timeout=self.__timeout,
        )

    def cleanup(self):
        """Clean up the client on disconnect."""

    #####################################################################################
    # Methods to handle callback functions

    def get_callback_id(self, callback):
        """Return a unique identifier for the callback function."""

        if isinstance(callback, str):
            return callback

        # Generate a unique id for the function. Use the id() function to make the id
        # unique, but append the function name for a more human readable id.
        return f"{id(callback)}.{callback.__name__}"

    def has_callback(self, callback):
        """Return True if there is a callback registered already for the id."""

        callback_id = self.get_callback_id(callback)
        with self.__callback_lock:
            return callback_id in self.__callbacks

    def get_callback(self, callback_id):
        """Return the callback function for the id."""

        with self.__callback_lock:
            return self.__callbacks.get(callback_id)

    def set_callback(self, callback):
        """Store a callback function by id."""

        callback_id = self.get_callback_id(callback)
        with self.__callback_lock:
            self.__callbacks[callback_id] = callback
        return callback_id

    #####################################################################################
    # Methods to emitting events

    @check_result
    def call_threadsafe(self, *args, **kwargs):
        """Call the emit method in a thread-safe way."""

        # Set a default namespace, if not given.
        if kwargs.get("namespace") is None and self._default_namespace:
            kwargs["namespace"] = self._default_namespace

        with self.__message_queue_lock:
            return self.call(*args, **kwargs)

    def emit_threadsafe(self, *args, **kwargs):
        """Call the emit method in a thread-safe way."""

        # Set a default namespace, if not given.
        if kwargs.get("namespace") is None and self._default_namespace:
            kwargs["namespace"] = self._default_namespace

        with self.__message_queue_lock:
            self.emit(*args, **kwargs)

    @check_result
    def emit_threadsafe_async(self, *args, **kwargs):
        """Call the emit method in a thread-safe and non-GUI blocking way."""

        # Set up the response object that will get updated once the api request has returned
        # from the server.
        response = {
            "ack": False,    # The request was acknowledged (finished)
            "result": None,  # The request result
        }

        # Add the event callback to pass to the sio emit method, which will call this function
        # once the server returns.
        kwargs["callback"] = self._get_request_callback(response)
        
        # Emit the event
        self.emit_threadsafe(*args, **kwargs)

        # Wait for the callback to set the event result
        self._wait_for_response(response)
        return response.get("result")

    def _handle_server_error(self, error):
        """Handle an error returned by the server from an event."""

        raise(error)

    #####################################################################################
    # Methods to emit specific events

    def get_alias_api(self):
        """Return the Alias Python API module."""

        # Get information about the api module
        api_info = self.call_threadsafe("get_alias_api_info")

        filename = os.path.basename(api_info["file_path"]).split(".")[0]
        cache_filename = "{filename}{alias}_py{python}.json".format(
            filename=filename,
            alias=api_info["alias_version"],
            python=api_info["python_version"],
        )
        cache_filepath = os.path.join(tempfile.gettempdir(), cache_filename)

        cache_loaded = False
        if os.path.exists(cache_filepath):
            # Check file modified dates to see if the cache is still up to date.
            cache_last_modified = os.stat(cache_filepath).st_mtime
            if api_info["last_modified"] < cache_last_modified:
                try:
                    with open(cache_filepath, "r") as fp:
                        module_proxy = json.load(fp, cls=self.get_json_decoder())
                        cache_loaded = True
                except Exception:
                    # TODO log warning?
                    pass

        if not cache_loaded:
            # Make the request to get the api, and cache it.
            module_proxy = self.call_threadsafe("get_alias_api")
            with open(cache_filepath, "w") as fp:
                json.dump(module_proxy, fp=fp, cls=self.get_json_encoder())

        return module_proxy.get_or_create_module(self)


    # -------------------------------------------------------------------------------------------------------
    # Protected methods

    def _get_request_callback(self, response):
        """
        Return a function that can be passed as a callback to handle a socketio event callback.

        :param response: The response object to pass to the callback to set with the event result data.
        :type response: dict

        :return: The callback function.
        :rtype: function
        """

        def __request_callback(*result):
            """Callback invoked when emit finished. The result is the return value of the api request."""
            if len(result) == 1:
                response["result"] = result[0]
            else:
                response["result"] = result
            response["ack"] = True

        return __request_callback

    def _wait_for_response(self, response):
        """
        Wait for the server to set the response object.

        Override this default method to do any processing while waiting for the server to
        return the response value. For example, a client may need to ensure the GUI is not
        blocking if Alias needs to perform GUI events during the api request.

        The response object is a dictionary with two key-values:

            ack:
                type: bool
                description: True if the response has been acknowledged and result is set,
                             else False if the server has not completed the api request.
            result:
                type: any
                description: The return value from the server api request.

        :param response: The response object that will be set with the server result once the
            server completes the api request.
        :type response: dict
        """

        while not response.get("ack", False):
            self._process_events()
    
    def _process_events(self):
        """
        Process GUI events.

        This default method does nothing. Override it to provide custom event processing.
        """

        # By default, do nothing. Override this method to provide event processing handling
        # specific to the running application.
