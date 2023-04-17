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

# NOTE this may be replaced/not necessary if Alias Python API can execute itself in the main thread
# e.g. Alias Team to expose the asyncTask in the ext API headers


def execute_in_main_thread(func):
    """Decorator function to ensure function is executed in main thread."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # We need to create the invoker each time, because it gets moved to the main thread, at
        # which point the inovker is no longer safe to access from the thread executing to
        # invoke the function with the invoker
        invoker = create_invoker()
        if invoker:
            return invoker.invoke(func, *args, **kwargs)
        # No invoker, just run the function normally
        return func(*args, **kwargs)

    return wrapper


def create_invoker():
    """Create an object used to invoke function calls on the main thread when called from a different thread."""

    # from sgtk.platform.qt import QtGui, QtCore
    from PySide2 import QtCore, QtGui

    if not QtCore:
        return None

    # NOTE should we use QtGui.QApplication.instance()?
    instance = QtCore.QCoreApplication.instance()
    if not instance:
        return None
        # if not instance:
        #     try:
        #         # NOTE in debug mode cannot access the app instance!
        #         # ALSO, for Alias < 2024.0 we can't do this because Alias is not running Qt
        #         #
        #         # We may be in debug mode in which case we need to do some fancy footwork here..
        #         # this is due to using debug dlls in C++ but release in pyside2 python
        #         from PySide2 import QtGui
        #         import shiboken2
        #         instance = shiboken2.wrapInstance(shiboken2.getCppPointer(QtGui.QGuiApplication.instance())[0], QtGui.QGuiApplication)
        #     except Exception as e:
        #         import PySide2
        #         print(PySide2.__version__)

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
