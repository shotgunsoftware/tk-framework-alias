__PySide_QtGui = None
__PySide_QtWidgets = None
imported_qt = False
try:
    # Try to import from PySide2
    from PySide2 import QtCore
    import PySide2.QtGui as __PySide_QtGui
    import PySide2.QtWidgets as __PySide_QtWidgets

    imported_qt = True
except ImportError:
    pass

if not imported_qt:
    # Try PySide6
    try:
        from PySide6 import QtCore
        import PySide6.QtGui as __PySide_QtGui
        import PySide6.QtWidgets as __PySide_QtWidgets

        imported_qt = True
    except ImportError:
        pass

if not imported_qt:
    # Try PySide
    from PySide import QtCore, QtGui
else:
    # Patch PySide2/PySide6 to keep the QtGui interface consistent with PySide (Qt 4).
    # We don't try to cover all cases, only the QtGui module as we are using components
    # from that which are different between Qt 5 and 4. Approach is taken from the
    # `tk-core` `pyside2_patcher.py` module.
    def _move_attributes(dst, src, names):
        """
        Moves a list of attributes from one package to another.
        :param names: Names of the attributes to move.
        """
        for name in names:
            if not hasattr(dst, name):
                setattr(dst, name, getattr(src, name))

    import types

    QtGui = types.ModuleType("PySide.QtGui")

    # Combine the attributes of the QtWidgets and QtGui into a new QtGui module.
    _move_attributes(QtGui, __PySide_QtWidgets, dir(__PySide_QtWidgets))
    _move_attributes(QtGui, __PySide_QtGui, dir(__PySide_QtGui))


# Handle QRegExp / QRegularExpression
if hasattr(QtCore, "QRegularExpression"):
    qt_re_module = QtCore.QRegularExpression
    qt_re_module_is_regular_expression = True
else:
    # NOTE remove once Qt4 support is removed
    qt_re_module = QtCore.QRegExp
    qt_re_module_is_regular_expression = False
