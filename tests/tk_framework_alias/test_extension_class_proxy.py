# Copyright (c) 2026 Autodesk, Inc.

"""Tests for AliasApiExtensions vs gui.Menu client class construction."""

import types
from unittest import mock

from tk_framework_alias import extension_api_classes
from tk_framework_alias.client.socketio import proxy_wrapper


def _install_extension_on_module(module_proxy, class_wrapper):
    """Materialize a placeholder class and run the extension install hook."""

    module = types.ModuleType("alias_api")
    module.AliasApiExtensions = class_wrapper._create_object()
    module_proxy.data.setdefault("__module_name__", "alias_api")
    module_proxy.data["__members__"] = [
        ("AliasApiExtensions", class_wrapper),
    ]
    extension_api_classes.install_alias_api_extensions_on_module(module, module_proxy)
    return module


def test_install_replaces_wrappers_on_alias_api_module():
    """Module load must always expose a callable extension type (not raw wrappers)."""

    module_proxy = mock.Mock()
    module_proxy.data = {"__module_name__": "alias_api"}
    module_proxy.send_request.return_value = True

    func_proxy = proxy_wrapper.AliasClientFunctionProxyWrapper(
        {"__function_name__": "has_picked_items", "__is_method__": True}
    )
    func_proxy._init(module_proxy, "has_picked_items")
    bad_type = type(
        "AliasApiExtensions",
        (object,),
        {"has_picked_items": func_proxy},
    )
    module = types.ModuleType("alias_api")
    module.AliasApiExtensions = bad_type

    extension_api_classes.install_alias_api_extensions_on_module(module, module_proxy)

    instance = module.AliasApiExtensions()
    assert instance.has_picked_items() is True
    assert not isinstance(
        module.AliasApiExtensions.__dict__["has_picked_items"],
        proxy_wrapper.AliasClientFunctionProxyWrapper,
    )


def test_alias_api_extensions_uses_local_instance():
    """AliasApiExtensions() stays on the client (no server constructor RPC)."""

    module_proxy = mock.Mock()
    wrapper = proxy_wrapper.AliasClientClassProxyWrapper(
        {
            "__module_name__": "alias_api",
            "__class_name__": "AliasApiExtensions",
            "__members__": [],
        }
    )
    wrapper._init(module_proxy, "AliasApiExtensions")
    cls = wrapper._create_object()
    instance = cls()
    assert type(instance).__name__ == "AliasApiExtensions"
    assert not hasattr(instance, "unique_id")
    module_proxy.send_request.assert_not_called()


def test_extension_rpc_via_module_install():
    """Extension instance methods RPC without server-side object ids."""

    module_proxy = mock.Mock()
    module_proxy.send_request.return_value = True
    wrapper = proxy_wrapper.AliasClientClassProxyWrapper(
        {
            "__module_name__": "alias_api",
            "__class_name__": "AliasApiExtensions",
            "__members__": [
                (
                    "has_picked_items",
                    {
                        "__function_name__": "has_picked_items",
                        "__is_method__": True,
                    },
                ),
            ],
        }
    )
    wrapper._init(module_proxy, "AliasApiExtensions")
    module = _install_extension_on_module(module_proxy, wrapper)

    assert module.AliasApiExtensions().has_picked_items() is True
    module_proxy.send_request.assert_called_once_with(
        "has_picked_items",
        {
            "__function_name__": "has_picked_items",
            "__function_args__": (),
            "__function_kwargs__": {},
            "__alias_api_extension_class__": "AliasApiExtensions",
        },
    )


def test_pybind_class_uses_server_side_constructor():
    """Pybind types such as Stage forward ``()`` to the Alias server."""

    module_proxy = mock.Mock()
    module_proxy.send_request.return_value = mock.sentinel.stage_proxy
    wrapper = proxy_wrapper.AliasClientClassProxyWrapper(
        {
            "__module_name__": "alias_api.stages",
            "__class_name__": "Stage",
            "__members__": [],
        }
    )
    wrapper._init(module_proxy, "Stage")
    cls = wrapper._create_object()

    result = cls("StageName", "path/to/stage")
    module_proxy.send_request.assert_called_once_with(
        "Stage",
        {
            "__function_name__": "Stage",
            "__function_args__": ("StageName", "path/to/stage"),
            "__function_kwargs__": {},
            "__request_module_name__": "alias_api.stages",
        },
    )
    assert result is mock.sentinel.stage_proxy


def test_gui_menu_item_uses_server_constructor_rpc():
    """gui.MenuItem must be created on the Alias server for menubar wiring."""

    module_proxy = mock.Mock()
    module_proxy.send_request.return_value = mock.sentinel.item_proxy

    wrapper = proxy_wrapper.AliasClientClassProxyWrapper(
        {
            "__module_name__": "alias_api.gui",
            "__class_name__": "MenuItem",
            "__members__": [],
        }
    )
    wrapper._init(module_proxy, "MenuItem")
    cls = wrapper._create_object()

    result = cls("My command", lambda: None)
    module_proxy.send_request.assert_called_once_with(
        "MenuItem",
        {
            "__function_name__": "MenuItem",
            "__function_args__": ("My command", mock.ANY),
            "__function_kwargs__": {},
            "__request_module_name__": "alias_api.gui",
        },
    )
    assert result is mock.sentinel.item_proxy


def test_gui_menu_uses_server_constructor_rpc():
    """gui.Menu still forwards construction to Alias over socketio."""

    module_proxy = mock.Mock()
    module_proxy.send_request.return_value = mock.sentinel.menu_proxy

    wrapper = proxy_wrapper.AliasClientClassProxyWrapper(
        {
            "__module_name__": "alias_api.gui",
            "__class_name__": "Menu",
            "__members__": [],
        }
    )
    wrapper._init(module_proxy, "Menu")
    cls = wrapper._create_object()

    result = cls("Test menu")
    module_proxy.send_request.assert_called_once_with(
        "Menu",
        {
            "__function_name__": "Menu",
            "__function_args__": ("Test menu",),
            "__function_kwargs__": {},
            "__request_module_name__": "alias_api.gui",
        },
    )
    assert result is mock.sentinel.menu_proxy


def test_root_alias_api_menu_uses_server_constructor_rpc():
    """alias_api.Menu (pre-2027.1 menubar) forwards construction to Alias."""

    module_proxy = mock.Mock()
    module_proxy.send_request.return_value = mock.sentinel.menu_proxy

    wrapper = proxy_wrapper.AliasClientClassProxyWrapper(
        {
            "__module_name__": "alias_api",
            "__class_name__": "Menu",
            "__members__": [],
        }
    )
    wrapper._init(module_proxy, "Menu")
    cls = wrapper._create_object()

    result = cls("ShotGrid")
    module_proxy.send_request.assert_called_once_with(
        "Menu",
        {
            "__function_name__": "Menu",
            "__function_args__": ("ShotGrid",),
            "__function_kwargs__": {},
            "__request_module_name__": "alias_api",
        },
    )
    assert result is mock.sentinel.menu_proxy


def test_legacy_pybind_class_replaces_encoded_new_stub():
    """Encoded ``__new__`` instance-method stubs are replaced with server construction."""

    module_proxy = mock.Mock()
    module_proxy.send_request.return_value = mock.sentinel.layer_proxy
    func_proxy = proxy_wrapper.AliasClientFunctionProxyWrapper(
        {"__function_name__": "__new__", "__is_method__": True}
    )
    func_proxy._init(module_proxy, "__new__")
    wrapper = proxy_wrapper.AliasClientClassProxyWrapper(
        {
            "__module_name__": "alias_api",
            "__class_name__": "Layer",
            "__members__": [("__new__", func_proxy)],
        }
    )
    wrapper._init(module_proxy, "Layer")
    cls = wrapper._create_object()

    assert isinstance(cls.__dict__["__new__"], staticmethod)
    assert cls("LayerName") is mock.sentinel.layer_proxy
