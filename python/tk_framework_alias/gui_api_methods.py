# Copyright (c) 2026 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

"""
Explicit RPC method list for ``alias_api.gui`` types (Alias 2027.1+).

Why this exists:
  - FPTR builds menus from the client process using ``gui.Menu`` / ``MainMenu`` proxies.
  - pybind11 often exposes ``add_item``, ``remove_menu``, etc. only on instances, not on
    the Python class, so API cache introspection misses them.
  - Without these entries, client ``Menu`` proxies have no instance methods and menu
    rebuild (clean on context change) fails.

Submodules like ``alias_api.stages`` stay as lightweight stubs because the engine
mostly holds server object handles; ``gui`` is special-cased in server_json and
proxy_wrapper (see comments there).

Do not use this for server-side menu building; menus are driven from tk-alias
``menu_generation`` via client proxies only.
"""

GUI_CLASS_INSTANCE_METHODS = {
    "Menu": (
        "add_item",
        "add_menu",
        "remove_item",
        "remove_menu",
        "remove",
    ),
    "MainMenu": (
        "add_item",
        "add_menu",
        "remove_item",
        "remove_menu",
        "remove",
    ),
}
