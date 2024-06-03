# -
# *****************************************************************************
# Copyright 2023 Autodesk, Inc. All rights reserved.
#
# These coded instructions, statements, and computer programs contain
# unpublished proprietary information written by Autodesk, Inc. and are
# protected by Federal copyright law. They may not be disclosed to third
# parties or copied or duplicated in any form, in whole or in part, without
# the prior written consent of Autodesk, Inc.
# *****************************************************************************
# +

try:
    import sys
    sys.path.append("C:\\python_libs")
    import ptvsd
    ptvsd.enable_attach()
    ptvsd.wait_for_attach()
except:
    pass


import sys
print(sys.version)
import threading


try:
    from PySide2 import QtCore, QtGui, QtWidgets
    from PySide2 import QtWebEngineWidgets, QtWebChannel, QtCore
    # from shiboken2 import wrapInstance
except ModuleNotFoundError:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6 import QtWebEngineWidgets, QtWebChannel, QtCore
    # from shiboken6 import wrapInstance



###############################################################################
# Alias Flow Plugin
###############################################################################


class PythonPlugin:
    """Alias plugin for Python."""

    def __init__(self):
        """Constructor"""

        self.__dialog = None
        self.__aliaspy = None
        self.__sio = None
        self.__qt_app = None
        self.__console_widget = None

        # Invoker must be created in the Main GUI thread
        self.__invoker = Invoker()

        # global host_service
        # host_service = MEDataPluginHostService(widget=None)
        # try:
        #     MEDataHostService.register_delegate(host_service)
        # except RuntimeError:
        #     # Delegate already registered
        #     pass

        # # Must happen after Qt app is created
        # self.__view = None
        # self.__channel = None

    def __del__(self):
        print("Destroying Alias Python Plugin...")

    # -------------------------------------------------------------------------
    # Properties

    @property
    def aliaspy(self):
        return self.__aliaspy

    @property
    def qt_app(self):
        return self.__qt_app

    # -------------------------------------------------------------------------
    # Private methods

    def create_qt_app(self):
        app_name = "Alias Python Plugin"
        self.__qt_app = QtWidgets.QApplication([app_name])
        self.__qt_app.setApplicationName(app_name)
        self.__qt_app.setQuitOnLastWindowClosed(False)
        QtWidgets.QApplication.instance().aboutToQuit.connect(
            lambda: QtWidgets.QApplication.processEvents()
        )

    def init_api(self, hostname=None, port=None, namespace=None, force=False):
        """
        Initialize the Alias Python api module to allow communication with Alias.

        The api can be initialized for either OpenAlias (GUI) or OpenModel (headless/batch)
        mode.

        For OpenAlias, the hostname, port and namespace arguments must be provided. These are
        required to connect to the running instance of Alias via a socketio server, which will
        provide the Alias API access.

        For OpenModel, none of the arguments are needed. Instead of connecting to a server to
        access the Alias API, the Alias Python API module can be directly imported (since it
        does not need to communicate with a running instance of Alias).

        :param hostname: For OpenAlias, the server host name to connect to, to access the api.
        :type hostname: str
        :param port: For OpenAlias, the server port to connect to, to access the api.
        :type port: int
        :param namespace: For OpenAlias, the server namespace to connect to, to access the api.
        :type namespace: str
        :param force: Force the api to be initialized, even if it has already been initialized.
        :type force: bool
        """

        if self.__aliaspy and not force:
            # Already initialized.
            return

        # Flow Production Tracking is running in a separate process than Alias. This is the new way how
        # the engine operates: the Alias plugin will bootstrap the engine in a separate
        # process than Alias (to avoid Qt conflicts between QtQuick/QML and QWidgets).
        # 
        # Run in OpenAlias mode, an instance of Alias should be running with a server
        # listening for client connections to communicate with. Using the socket
        # communication, the api will be imported.

        # Default connection values
        hostname = hostname or "127.0.0.1"
        port = port or 8000
        namespace = namespace or "/alias-python"

        connected = self.__setup_sio(hostname, port, namespace)
        if not connected:
            raise Exception("Failed to connect to Alias api server")

        # Get the server info and api module through the socket connection
        api_module = self.__sio.get_alias_api()
        if not api_module:
            raise Exception("Failed to get Alias Python API for OpenAlias.")

        # Create the AliasPy object to wrap the api module. All Alias api requests can be made
        # directly with the AliasPy object, it will route the request to the actual api module
        self.__aliaspy = api_module
        # self.__aliaspy = self._tk_alias.AliasPy(api_module)

        # Allow the AliasPy object to be imported. This is for backward compatibility with
        # previous engine versions aceessing the alias_api.pyd module directly through import
        sys_module_name = "alias_api"
        sys.modules[sys_module_name] = self.__aliaspy

        try:
            # Sanity check that the module can be imported.
            import alias_api

            assert alias_api is self.__aliaspy
        except Exception as import_error:
            raise Exception(
                f"Failed to set up the Alias Python API module\n{import_error}"
            )

    def __setup_sio(self, hostname, port, namespace):
        """
        Set up the socketio communication with Alias.

        Create a socketio client to connect to the running Alias server.

        :param hostname: The api server host name to connect to.
        :type hostname: str
        :param port: The api server port name to connect to.
        :type port: int
        :param namespace: The api server namespace to connect to.
        :type namespace: str

        :return: True if the socketio client was created and is connected to the server, False
            otherwise.
        :rtype: bool
        """

        from tk_framework_alias.client import AliasSocketIoClient, AliasClientNamespace

        # Create and connect to the server to communicate with Alias
        self.__sio = AliasSocketIoClient(namespace, execute_in_main_thread_func=self.execute_in_main_thread)
        self.__sio._default_namespace = namespace
        self.__sio._process_events = self.process_events
        # self.__sio = AliasSocketIoClient(namespace, request_timeout=60*3)

        flow_namespace = AliasClientNamespace(namespace)
        self.__sio.add_namespace(flow_namespace)

        if not self.__sio:
            raise Exception("Failed to create socketio client")

        # Connect to the server to start communicating
        self.__sio.start(hostname, port)

        # Return the connection status
        return self.__sio.connected

    # -------------------------------------------------------------------------
    # Public methods

    def open_console(self):
        print("Opening Console...")

        from tk_framework_alias.client.gui.console import console

        if not self.__console_widget:
            self.__console_widget = console.PythonConsoleWidget()

        self.__console_widget.show()

    def process_events(self):
        """
        Process GUI events.

        ShotGrid runs a Qt application for its GUI, so this method will process Qt GUI events,
        excluding user input events.

        This method is called while waiting for an sio event to return. This allows Alias to
        perform any necessary GUI events during an api request from the client (else
        the app may become deadlocked if the client makes an api request while blocking GUI
        events, but the api requests needs to perform some actions in the GUI).
        """

        if self.qt_app:
            self.qt_app.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

    def execute_in_main_thread(self, func, *args, **kwargs):
        """
        """
        # Execute in main thread might be called before the invoker is ready.
        # For example, an engine might use the invoker for logging to the main
        # thread.
        if not self.__invoker:
            return

        if (
            QtWidgets.QApplication.instance()
            and QtCore.QThread.currentThread()
            != QtWidgets.QApplication.instance().thread()
        ):
            # invoke the function on the thread that the QtGui.QApplication was created on.
            return self.__invoker.invoke(func, *args, **kwargs)
        else:
            # we're already on the main thread so lets just call our function:
            return func(*args, **kwargs)

class Invoker(QtCore.QObject):
    """
    Invoker class - implements a mechanism to execute a function with arbitrary
    args in the main thread.
    """

    def __init__(self):
        """
        Construction
        """
        QtCore.QObject.__init__(self)
        self._lock = threading.Lock()
        self._fn = None
        self._res = None

    def invoke(self, fn, *args, **kwargs):
        """
        Invoke the specified function with the specified args in the main thread

        :param fn:          The function to execute in the main thread
        :param *args:       Args for the function
        :param **kwargs:    Named arguments for the function
        :returns:           The result returned by the function
        """
        # acquire lock to ensure that the function and result are not overwritten
        # by syncrounous calls to this method from different threads
        self._lock.acquire()
        try:
            self._fn = lambda: fn(*args, **kwargs)
            self._res = None

            # invoke the internal _do_invoke method that will actually run the function.  Note that
            # we are unable to pass/return arguments through invokeMethod as this isn't properly
            # supported by PySide.
            QtCore.QMetaObject.invokeMethod(
                self, "_do_invoke", QtCore.Qt.BlockingQueuedConnection
            )

            return self._res
        finally:
            self._lock.release()

    @QtCore.Slot()
    def _do_invoke(self):
        """
        Execute the function
        """
        self._res = self._fn()


###############################################################################
# Add the Flow Plugin to the Alias menu
###############################################################################

def start_client(hostname, port, namespace):
    python_plugin = PythonPlugin()
    python_plugin.init_api(hostname, int(port), namespace)

    # Must import after flow created
    # import alias_api
    alias_api = python_plugin.aliaspy

    python_menu = alias_api.Menu("Python")
    python_menu.add_command("Open Console", lambda: python_plugin.open_console())

    python_plugin.create_qt_app()
    alias_api.log_to_prompt("We have Python!!")
    ret = python_plugin.qt_app.exec()

    print("Exiting Alias Python...")
    return ret


if __name__ == "__main__":
    """
    Bootstrap the Flow Production Tracking Alias Engine application.

    This script calls the `bootstrap_engine` method with the script args to do the work.

    The exepcted arguments are:
        1. this script name
        2. host name of a running socketio server
        3. port of the running socketio server
        4. namespace of the running socketio server.
        5. the pipeline config id to bootstrap with

    Before this script is called, it is expected that a socketio server is running on the
    given host, port and the namespace is a valid namespace for the server.

    It is designed, but not limited, to be called from the AliasPy plugin (found in
    tk-framework-alias). The AliasPy plugin will start a socketio server running on the given
    host and port, and has the given namespace. The path to this script is given to the plugin
    via the enviroment variable `ALIAS_PLUGIN_CLIENT_EXECPATH`, which allows the plugin to
    execute this script in a new process, giving the server info for this script to use to
    connect to the running server.
    """

    print("Starting Alias Python plugin...")
    args = sys.argv[1:]
    ret = start_client(*args)
    sys.exit(ret)
