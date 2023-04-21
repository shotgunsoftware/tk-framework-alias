# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import json
import os
import socketio
import threading
import tempfile

from .client_json import AliasClientJSON


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

    def emit_threadsafe(self, *args, **kwargs):
        """Call the emit method in a thread-safe way."""

        # Set a default namespace, if not given.
        if kwargs.get("namespace") is None and self._default_namespace:
            kwargs["namespace"] = self._default_namespace

        with self.__message_queue_lock:
            self.emit(*args, **kwargs)

    def call_threadsafe(self, *args, **kwargs):
        """Call the emit method in a thread-safe way."""

        # Set a default namespace, if not given.
        if kwargs.get("namespace") is None and self._default_namespace:
            kwargs["namespace"] = self._default_namespace

        with self.__message_queue_lock:
            return self.call(*args, **kwargs)

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

        # FIXME TEMP force cache reload
        # cache_loaded = False
        if not cache_loaded:
            # Make the request to get the api, and cache it.
            module_proxy = self.call_threadsafe("get_alias_api")
            with open(cache_filepath, "w") as fp:
                json.dump(module_proxy, fp=fp, cls=self.get_json_encoder())

        return module_proxy.get_or_create_module(self)
