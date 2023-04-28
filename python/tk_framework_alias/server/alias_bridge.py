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
import subprocess
import sys
import threading

# Third party pacakges included in dist/pkgs.zip
import socketio
import eventlet

from .socketio.data_model import AliasDataModel
from .socketio.server_json import AliasServerJSON
from .socketio.namespaces.server_namespace import AliasServerNamespace
from .socketio.namespaces.events_namespace import AliasEventsServerNamespace
from .socketio.namespaces.events_client_namespace import (
    AliasEventsClientNamespace,
)
from .utils.singleton import Singleton
from .utils.wsgi_server_logger import WSGIServerLogger


class AliasBridge(metaclass=Singleton):
    """
    A class to handle communication with Alias.

    The AliasBridge is responsible for starting a socketio server that listens for Alias
    clients to connect to, in order to communicate with a running instance of Alias. The
    server can execute Alias API requests such that external clients can interact with Alias.

    In addition to the socketio server, the bridge creates a socketio client that handles
    events Alias triggered from Alias. This Alias event client forwards the socketio events to
    the server which then sends it to all other connected clients. This Alias event client is
    required because the server can only execute in the thread it was created it, but Alias
    events trigger the socketio event in the Alias main thread.
    """

    def __init__(self):
        """Initialize the bridge."""

        # import sys
        # sys.path.append("C:\\python_libs")
        # import ptvsd
        # ptvsd.enable_attach()
        # ptvsd.wait_for_attach()

        # Default server socket params
        self.__default_hostname = "127.0.0.1"
        self.__default_port = 8000
        self.__max_retry_count = 25
        self.__server_socket = None

        # Create the SocketIO server, support long-polling (default) and websocket transports.
        # We will try to use websocket transport, if possible
        self.__server_sio = socketio.Server(
            aysnc_mode="eventlet",
            logger=True,
            engineio_logger=True,
            ping_interval=120,
            json=AliasServerJSON,
        )

        # Register a namespace to handle Alias events specifically
        self.__server_sio.register_namespace(AliasEventsServerNamespace())

        # Create the WSGI middleware for the SocketIO server
        self.__app = socketio.WSGIApp(self.__server_sio, static_files={})
        self.__wsgi_logger = WSGIServerLogger()

        # Create the SocketIO client to handle Alias events in the main thread
        self.__alias_events_client_sio = socketio.Client(
            logger=True, engineio_logger=True
        )
        self.__alias_events_client_sio.register_namespace(AliasEventsClientNamespace())

        # Create the Alias data model to store Alias objects to look up
        self.__data_model = AliasDataModel()

        # Track the clients registered to the socketio server
        self.__clients = {}

    # Properties
    # ----------------------------------------------------------------------------------------

    @property
    def alias_data_model(self):
        """Get the Alias Data Model to access Alias objects."""
        return self.__data_model

    @property
    def alias_events_client_sio(self):
        """Get the client socketio that can be used to emit Alias events to the server."""
        return self.__alias_events_client_sio

    # Public methods
    # ----------------------------------------------------------------------------------------

    def get_hostname(self):
        """Return the name of the host that this server socket is listening on."""

        if not self.__server_socket:
            return None
        return self.__server_socket.getsockname()[0]

    def get_port(self):
        """Return the port number that this server socket is listening on."""

        if not self.__server_socket:
            return None
        return self.__server_socket.getsockname()[1]

    def start_server(self, host=None, port=None, max_retries=None):
        """
        Start the server to communicate between Alias and ShotGrid.

        This will create a new thread to serve the WSGI server application to listen for
        client connections to the socketio server.

        :param host: The host name to open the socket server on.
        :type host: str
        :param port: The port number to open the socket server on.
        :type port: int
        :param max_retries: The number of retries to create the socket server.
        :type max_retries: int

        :return: True if the server started successfully, else False.
        :rtype: bool

        :raises Exception: If the socket failed to be created.
        """

        if self.__server_socket:
            # Already started
            return True

        # First, find an open port on the host for the server socket to listen on.
        self.__server_socket = self.__create_server_socket(host, port, max_retries)
        if not self.__server_socket:
            raise Exception("Failed to create server socket.")

        # Start the SocketIO server in a new thread using Python standard threds.
        th = threading.Thread(target=self.__serve_app)
        th.start()

        # Connect the Alias socketio client to the server. This must be called after the server is started in a new thread.
        server_host, server_port = self.__server_socket.getsockname()
        self.alias_events_client_sio.connect(
            f"http://{server_host}:{server_port}",
            namespaces=[AliasEventsServerNamespace.get_namespace()],
            wait_timeout=20,
        )

        return True

    def stop_server(self):
        """Stop the server."""

        if self.alias_events_client_sio:
            # The shutdown must be emitted from the alias events client because we will execute
            # this function from the main thread (not the thread that the socketio server is
            # executing in), and the socketio server can only be accessed from the single thread
            # it executes in.
            self.alias_events_client_sio.call(
                "shutdown", namespace=AliasEventsServerNamespace.get_namespace()
            )
            self.alias_events_client_sio.disconnect()

    def get_client_by_namespace(self, namespace):
        """Return the client for the given namespace."""

        return next(
            (
                client_data
                for client_data in self.__clients.values()
                if client_data["namespace"] == namespace
            ),
            {},
        )

    def register_client_namespace(self, client_name, client_exe_path, client_info):
        """
        Register a new client.

        A client is unique by the `client_name`. A socketio.Namespace will be created for the
        client and registered to the server.

        If the client already has been registered, the client data will be returned.
        """

        if self.__clients.get(client_name):
            raise Exception("Client already registered")

        namespace_handler = AliasServerNamespace(client_name)
        self.__server_sio.register_namespace(namespace_handler)

        client = {
            "name": client_name,
            "exe_path": client_exe_path,
            "info": client_info,
            "namespace": namespace_handler.namespace,
        }
        self.__clients[client_name] = client

        return client

    def bootstrap_client(self, client_name, client_exe_path, client_info=None):
        """
        Bootstrap the Alias client.

        This method does not start the server; if the client process needs to connect to the
        sever on bootstrap, the server should already be started to ensure it is ready for the
        client to connect to.
        """

        client = self.__clients.get(client_name)
        if not client:
            client = self.register_client_namespace(
                client_name, client_exe_path, client_info
            )

        # Get the python interpreter to use from the environment, fallback to checking the
        # current interpreter if not set.
        python_exe = os.environ.get("ALIAS_PLUGIN_CLIENT_PYTHON")
        if not python_exe:
            if os.path.basename(sys.executable) != "python.exe":
                # We may be embedded, in which case the exe will be the running application instaed of
                # the python exe
                # Try to construct the python exe from the exec prefix
                python_exe = os.path.join(sys.exec_prefix, "python.exe")
                if not os.path.exists(python_exe):
                    # Fall back to the sys.executable, in could be a specific pythonXY.exe
                    python_exe = sys.executable
            else:
                python_exe = sys.executable

        # Set up the args to start the new process
        args = [
            python_exe,
            client["exe_path"],
            self.get_hostname(),
            str(self.get_port()),
            client["namespace"],
        ]

        # Copy the env variables to start the new process with
        startup_env = os.environ.copy()

        # Set up the startup info for opening the new process.
        si = subprocess.STARTUPINFO()
        # Only show the console window when in debug mode.
        if os.environ.get("ALIAS_PLUGIN_CLIENT_DEBUG") != "1":
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Start the client in a new a process, don't wait for it to finish.
        result = subprocess.Popen(args, env=startup_env, startupinfo=si)

        return True

    def restart_client(self, client_namespace):
        """Re-bootstrap the client for the given namespace."""

        client = self.get_client_by_namespace(client_namespace)
        if not client:
            # TODO log warning
            return

        return self.bootstrap_client(client["name"], client["exe_path"], client["info"])

    # Private methods
    # ----------------------------------------------------------------------------------------

    def __create_server_socket(self, host, port, max_retries):
        """Open a server socket and return the socket."""

        host = host or self.__default_hostname
        port = port or self.__default_port
        max_retry_count = max_retries or self.__max_retry_count

        server_socket = None
        retry_count = 0

        while server_socket is None and retry_count <= max_retry_count:
            try:
                # Open the server socket to start listening on
                return eventlet.listen((host, port))

            except OSError:
                # Address is already in use, try the next port.
                port += 1
                retry_count += 1

        return None

    def __serve_app(self):
        """Using eventlet, start the WSGI server application to listen for clients connections."""

        # Start the WSGI server to start handling requests from the server socket
        #
        # NOTE eventlet is not compatible with Python standard threads. There are issues trying
        # to use eventlet.monkey_patch, so we just need to ensure that the server acts as it is
        # single threaded (e.g. can only access the socketio server from the thread it was created
        # in).
        eventlet.wsgi.server(self.__server_socket, self.__app, log=self.__wsgi_logger)
