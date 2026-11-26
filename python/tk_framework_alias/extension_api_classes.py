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
Client-side class construction policy for the Alias API cache.

Cached pybind types normally forward client ``()`` to the Alias server and return an
instance proxy. ``AliasApiExtensions`` is plain Python and must stay on the client.
Menubar types listed in ``ALIAS_API_SERVER_CONSTRUCTED_CLASSES`` also need extra gui
RPC stubs (``gui_api_methods``).

Policy on the client:

- ``AliasApiExtensions``: local placeholder, then :func:`install_alias_api_extensions_on_module`
- All other cached classes: server-side ``()`` (e.g. ``Stage``, menu types)

Extension classes are (re)installed on the ``alias_api`` module after cache load so
menubar-related class-encoding changes cannot leave ``FunctionProxyWrapper`` objects
on the type dict (which are not callable from app code).
"""

import inspect

# tk-framework-alias extension types on ``alias_api`` (not pybind C++ classes).
ALIAS_API_EXTENSION_CLASSES = frozenset({"AliasApiExtensions"})
ALIAS_API_EXTENSIONS_CLASS_NAME = "AliasApiExtensions"

# Types that must be constructed in Alias and returned as client instance proxies.
# ``alias_api.Menu`` is the pre-2027.1 menubar entry point; 2027.1+ uses ``alias_api.gui``.
ALIAS_API_SERVER_CONSTRUCTED_CLASSES = frozenset(
    {
        ("alias_api", "Menu"),
        ("alias_api.gui", "Menu"),
        ("alias_api.gui", "MainMenu"),
        ("alias_api.gui", "MenuItem"),
    }
)


def uses_local_client_constructor(module_name, class_name):
    """
    Return True if ``()`` should build a lightweight client instance only.

    :rtype: bool
    """

    if class_name not in ALIAS_API_EXTENSION_CLASSES:
        return False
    return not module_name or module_name == "alias_api"


def uses_server_side_constructor(module_name, class_name):
    """
    Return True for menubar types that need ``gui_api_methods`` injection.

    These types are a subset of classes that server-construct on ``()`` (all pybind
    types except :func:`uses_local_client_constructor`). The allowlist marks menubar
    types for stub injection; it is not the only server-construction gate.

    :rtype: bool
    """

    return (module_name, class_name) in ALIAS_API_SERVER_CONSTRUCTED_CLASSES


def make_alias_api_extension_static_rpc(module_proxy, method_name):
    """
    Build a staticmethod RPC for ``alias_api.AliasApiExtensions`` members.

    Extension instances are lightweight client handles; methods always run on
    a fresh server-side ``AliasApiExtensions()`` and must not use the
    instance-method proxy path (which expects a server ``unique_id``).
    """

    def _invoke(*args, **kwargs):
        return module_proxy.send_request(
            method_name,
            {
                "__function_name__": method_name,
                "__function_args__": args,
                "__function_kwargs__": kwargs,
                "__alias_api_extension_class__": ALIAS_API_EXTENSIONS_CLASS_NAME,
            },
        )

    _invoke.__name__ = method_name
    return staticmethod(_invoke)


def _is_encoded_function_member(member_data, function_wrapper_cls):
    """Return True if a cache member entry describes an RPC function."""

    if isinstance(member_data, function_wrapper_cls):
        return True
    if isinstance(member_data, dict):
        return function_wrapper_cls.needs_wrapping(member_data)
    return False


def collect_alias_api_extension_method_names(
    ext_type,
    class_proxy_wrapper=None,
    function_wrapper_cls=None,
):
    """
    Gather extension method names from a client type, class proxy, or encoded cache.

    :rtype: set[str]
    """

    from .client.socketio.proxy_wrapper import (
        AliasClientClassProxyWrapper,
        AliasClientFunctionProxyWrapper,
    )

    if function_wrapper_cls is None:
        function_wrapper_cls = AliasClientFunctionProxyWrapper

    names = set()

    encoded_class = None
    if isinstance(class_proxy_wrapper, AliasClientClassProxyWrapper):
        encoded_class = class_proxy_wrapper.data
    elif isinstance(class_proxy_wrapper, dict):
        encoded_class = class_proxy_wrapper

    if encoded_class is not None:
        for attr_name, attr_data in encoded_class.get("__members__") or []:
            if attr_name.startswith("_"):
                continue
            if _is_encoded_function_member(attr_data, function_wrapper_cls):
                names.add(attr_name)

    if inspect.isclass(ext_type):
        for attr_name, attr_value in ext_type.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr_value, function_wrapper_cls):
                names.add(attr_name)
            elif callable(attr_value) and not isinstance(attr_value, type):
                names.add(attr_name)

    return names


def build_client_alias_api_extensions_type(module_proxy, method_names):
    """
    Build the client ``AliasApiExtensions`` type used by Toolkit apps.

    :param module_proxy: Root ``alias_api`` module proxy (socketio).
    :param method_names: Extension RPC names (e.g. ``has_picked_items``).
    :rtype: type
    """

    class_attrs = {
        "__init__": lambda self, *args, **kwargs: None,
        "__new__": staticmethod(object.__new__),
    }

    for method_name in sorted(method_names):
        class_attrs[method_name] = make_alias_api_extension_static_rpc(
            module_proxy, method_name
        )

    if method_names:

        def __getattr__(self, name):
            if name not in method_names:
                raise AttributeError(name)
            return make_alias_api_extension_static_rpc(module_proxy, name).__func__

        class_attrs["__getattr__"] = __getattr__

    return type(ALIAS_API_EXTENSIONS_CLASS_NAME, (object,), class_attrs)


def install_alias_api_extensions_on_module(module, module_proxy):
    """
    Replace cached ``alias_api.AliasApiExtensions`` with a dedicated client RPC type.

    Called after the API module is materialized from disk cache. This is the supported
    extension workflow entry point and is independent of how the class was encoded for gui
    menubar support in 2027.1.

    :param module: Materialized ``alias_api`` module on the Toolkit client.
    :param module_proxy: Root ``alias_api`` socketio module proxy.
    """

    from .client.socketio.proxy_wrapper import (
        AliasClientClassProxyWrapper,
        AliasClientObjectProxyWrapper,
    )

    if module.__dict__.get(ALIAS_API_EXTENSIONS_CLASS_NAME) is None:
        return

    class_proxy = None
    ext_type = module.__dict__[ALIAS_API_EXTENSIONS_CLASS_NAME]
    if isinstance(ext_type, AliasClientClassProxyWrapper):
        class_proxy = ext_type
        ext_type = None

    if class_proxy is None:
        for attr_name, attr_data in module_proxy.data.get("__members__") or []:
            if attr_name != ALIAS_API_EXTENSIONS_CLASS_NAME:
                continue
            if isinstance(attr_data, AliasClientClassProxyWrapper):
                class_proxy = attr_data
            break

    method_names = collect_alias_api_extension_method_names(
        ext_type,
        class_proxy_wrapper=class_proxy,
    )

    client_type = build_client_alias_api_extensions_type(module_proxy, method_names)
    module.__dict__[ALIAS_API_EXTENSIONS_CLASS_NAME] = client_type
    AliasClientObjectProxyWrapper.store_type(
        module_proxy.data["__module_name__"],
        ALIAS_API_EXTENSIONS_CLASS_NAME,
        client_type,
    )
