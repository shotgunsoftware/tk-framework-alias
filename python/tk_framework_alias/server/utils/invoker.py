# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

from functools import wraps
import threading

from .exceptions import QtImportError


def execute_in_main_thread(func):
    """
    Decorator function to ensure function is executed in main thread.

    This could be replaced with using the Alias API AlAsyncTask addAsyncTask function. Thex
    addAsyncTask function would execute the api function in the main thread synchronoushly
    with Alias events. Though, this requires refactoring Alias API requests to work in an
    asynchronous way.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # We need to create the invoker each time, because it gets moved to the main thread, at
        # which point the inovker is no longer safe to access from the thread executing to
        # invoke the function with the invoker
        try:
            invoker = create_invoker()
        except QtImportError as qt_error:
            return QtImportError(f"The version of PySide2 must match the Qt version that Alias is running with.\n{qt_error}")
        except Exception as error:
            return Exception(f"Failed to create invoker to execute function in the application main thread.\n{error}")

        return invoker.invoke(func, *args, **kwargs)
        
    return wrapper


def create_invoker():
    """Create an object used to invoke function calls on the main thread when called from a different thread."""

    try:
        from PySide2 import QtCore
    except Exception as e:
        raise QtImportError(e)

    if not QtCore:
        raise QtImportError("QtCore not found")

    instance = QtCore.QCoreApplication.instance()
    if not instance:
        # NOTE to developers, if Alias is running in debug then the PySide2 libraries used
        # must also be debug versions. If not, the Qt app instance will fail to be found.
        qt_version = QtCore.__version__
        raise QtImportError(f"Qt Application instance must be created first. Using PySide2 version {qt_version}")
        # raise Exception("Qt Application instance must be created first")

    # Classes are defined locally since Qt might not be available.
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

    # Make sure that the invoker exists in the main thread:
    invoker = Invoker()
    invoker.moveToThread(instance.thread())

    return invoker
