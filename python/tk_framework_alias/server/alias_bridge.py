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

sys.path.append("C:\\python_libs")
import ptvsd
ptvsd.enable_attach(address=('localhost', 5679))
ptvsd.wait_for_attach()

import eventlet
import socketio
import threading

from .socket_io.alias_data_model import AliasDataModel
from .socket_io.alias_server import AliasServer
from .socket_io.alias_server_json import AliasServerJSON
from .socket_io.namespaces.alias_events_namespace import AliasEventsServerNamespace
from .socket_io.namespaces.alias_events_client_namespace import AliasEventsClientNamespace
from .utils.singleton import Singleton
from .utils.wsgi_server_logger import WSGIServerLogger


class AliasBridge(metaclass=Singleton):
    """A class to handle communication with Alias."""

    def __init__(self):
        """Initialize the server."""

        # Default server socket params
        self.__default_hostname = "127.0.0.1"
        self.__default_port = 8080
        self.__max_retry_count = 25
        self.__server_socket = None
        
        # Create the SocketIO server, support long-polling (default) and websocket transports.
        # We will try to use websocket transport, if possible
        # self._server_sio = AliasServer(
            # plugin_version,
            # alias_version,
            # python_version,
        self.__server_sio = socketio.Server(
            aysnc_mode="eventlet",
            logger=True,
            engineio_logger=True,
            ping_interval=120,
            json=AliasServerJSON,
        )
        self.__server_sio.register_namespace(AliasEventsServerNamespace())

        # Create the WSGI middleware for the SocketIO server
        self.__app = socketio.WSGIApp(self.__server_sio, static_files={})
        self.__wsgi_logger = WSGIServerLogger()

        # Create the SocketIO client to handle Alias events in the main thread
        self.__alias_events_client_sio = socketio.Client(logger=True, engineio_logger=True)
        self.__alias_events_client_sio.register_namespace(AliasEventsClientNamespace())

        # Create the Alias data model to store Alias objects to look up
        self.__data_model = AliasDataModel()

        # Track the namespaces registered to the socketio server
        self.__connectors = {}


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

    @property
    def alias_data_model(self):
        """Get the Alias Data Model to access Alias objects."""
        return self.__data_model

    @property
    def alias_events_client_sio(self):
        """Get the client socketio that can be used to emit Alias events to the server."""
        return self.__alias_events_client_sio

    def start(self, host=None, port=None, max_retries=None):
        """
        Start the server to communicate between Alias and ShotGrid.

        This will create a new thread to serve the WSGI server application to listen for
        client connections to the socketio server.
        """

        if self.__server_socket:
            # Already started
            return True

        # First, find an open port on the host for the server socket to listen on.
        self.__server_socket = self.__create_server_socket(host, port, max_retries)
        if not self.__server_socket:
            # Failed to open a server socket.
            raise Exception("Failed to open server socket.")
    
        # Start the SocketIO server in a new thread using Python standard threds.
        th = threading.Thread(target=self.__serve_app)
        # th.daemon = True
        th.start()

        # Connect the Alias socketio client to the server. This must be called after the server is started in a new thread.
        server_host, server_port = self.__server_socket.getsockname()
        self.alias_events_client_sio.connect(
            f"http://{server_host}:{server_port}",
            namespaces=[AliasEventsServerNamespace.get_namespace()],
            wait_timeout=20,
        )

        return True 

    def stop(self):
        """Stop the server."""

        if self.alias_events_client_sio:
            # The shutdown must be emitted from the alias events client because we will execute
            # this function from the main thread (not the thread that the socketio server is
            # executing in), and the socketio server can only be accessed from the single thread
            # it executes in.
            self.alias_events_client_sio.call("shutdown", namespace=AliasEventsServerNamespace.get_namespace())
            self.alias_events_client_sio.disconnect()

        # TODO close the server socket?
        # TODO shutdown the server so it could be reloaded?

    def register_connector(self, connector, namespace):
        """Register a new connection."""

        namespance_name = namespace.namespace
        if namespance_name in self.__server_sio.namespaces:
            # TODO more specific exception
            raise Exception(f"Namespace '{namespance_name}' already in use. Connector not registered")

        self.__connectors[namespance_name] = connector
        self.__server_sio.register_namespace(namespace)

    def get_connector_by_namespace(self, namespace):
        """Return the connector object for the given namespace."""

        return self.__connectors.get(namespace)

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

    def bootstrap_client(self, client_exe_path, namespace):
        """
        Bootstrap the Alias client.

        This method does not start the server; if the client process needs to connect to the
        sever on bootstrap, the server should already be started to ensure it is ready for the
        client to connect to.
        """

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
            client_exe_path,
            self.get_hostname(),
            str(self.get_port()),
            namespace
        ]

        # Store the main Alias process id in the environment
        os.environ["ALIAS_PID"] = str(os.getpid())
        startup_env = os.environ.copy()

        # Set up the startup info for opening the new process.
        si = subprocess.STARTUPINFO()
        # Only show the console window when in debug mode.
        if os.environ.get("ALIAS_PLUGIN_CLIENT_DEBUG") != "1":
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Start the client in a new a process, don't wait for it to finish.
        subprocess.Popen(args, env=startup_env, startupinfo=si)

        return True
