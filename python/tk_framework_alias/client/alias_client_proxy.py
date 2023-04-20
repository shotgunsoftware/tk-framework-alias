# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import inspect
import threading
import types

from .exceptions import ClientNotConnected, ClientNotFound


class AliasClientObjectProxyWrapper:
    """Wrapper class for Alias objects."""

    __modules = {}
    __module_lock = threading.Lock()

    def __init__(self, data):
        """Initialize the proxy wrapper object."""

        self.__data = data or {}

    @staticmethod
    def _get_module_attributes(module, members):
        """Return an attributes dictionary from the member data."""

        if not members:
            return {}

        attrs = {}
        for member_name, member_object in members:
            if isinstance(member_object, AliasClientModuleAttributeProxy):
                attribute = member_object.create_attribute(module, member_name)
                attrs[member_name] = attribute
            else:
                attrs[member_name] = member_object

        return attrs

    @classmethod
    def get_module(cls, module_name):
        """Return the module for the given name."""

        with cls.__module_lock:
            return cls.__modules.get(module_name)

    @classmethod
    def store_module(cls, module_name, module):
        """Store the module."""

        with cls.__module_lock:
            cls.__modules[module_name] = module

    @classmethod
    def create(cls, data):
        """Factory method to create an AliasClientModuleAttributeProxy object."""

        if not isinstance(data, dict):
            return None

        subclasses = cls.__subclasses__()
        while subclasses:
            subclass = subclasses.pop()
            if getattr(subclass, "needs_wrapping")(data):
                return subclass._create(data)

            # Add subclasses of this class, if not found
            subclasses.extend(subclass.__subclasses__())

        return None

    @classmethod
    def _create(cls, data):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        return cls(data)

    @property
    def data(self):
        return self.__data

    def sanitize(self):
        """Return a sanitized representation of this proxy that is JSON serializable."""
        return self.data



class AliasClientModuleProxy(AliasClientObjectProxyWrapper):
    """A proxy class to represent an Alias Python API module."""


    def __init__(self, module_data):
        """Initialize"""

        super(AliasClientModuleProxy, self).__init__(module_data)

        self.__sio = None
        self.module_name = self.data["__module_name__"]


    @classmethod
    def needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set(
            [
                "__module_name__",
                "__members__",
            ]
        )
        value_keys = set(value)
        return required_keys == value_keys

    @property
    def sio(self):
        """Get the socketio client that this module uses to send and receive messages with Alias."""
        return self.__sio

    def get_or_create_module(self, sio):
        """Get or create the module."""

        self.__sio = sio

        module = self.get_module(self.module_name)

        if not module:
            # Create the new module, and set its attributes
            module = types.ModuleType(self.module_name)
            module_attrs = self._get_module_attributes(self, self.data["__members__"])
            module.__dict__.update(module_attrs)
            # Store the module
            self.store_module(self.module_name, module)
        
        return module


class AliasClientModuleAttributeProxy(AliasClientObjectProxyWrapper):
    """The base abstract class to represent an Alias client module attribute."""

    def __init__(self, data):
        """Initialize"""

        super(AliasClientModuleAttributeProxy, self).__init__(data)

        self.__module = None
        self.__name = None


    @classmethod
    def needs_wrapping(cls, value):
        """Return False, subclass must implement."""
        return False

    @property
    def module(self):
        """Get the module this attribute belogns to."""
        return self.__module

    @property
    def name(self):
        """Get the name of this attribute."""
        return self.__name

    @property
    def sio(self):
        """Get the socketio client to communicate with Alias."""
        return self.__module.sio

    def init(self, module, attribute_name):
        """
        Initialize the attribute.
        
        This must be called before the module attribute is used.

        Set the module that this attribute belongs to.
        """

        self.__module = module
        self.__name = attribute_name

    def create_attribute(self, module, attribute_name):
        """Create the attribute object for the module."""

        self.init(module, attribute_name)
        return self._create(self.data)

    def send_request(self, func_name, func_data):
        """Send an API request to the server."""

        response = {
            "ack": False,
            "result": None,
        }

        def __get_request_callback(response):
            def __callback(*result):
                if len(result) == 1:
                    response["result"] = result[0]
                else:
                    response["result"] = result
                response["ack"] = True

            # TODO set the results so that the main thread gets these values back
            return __callback

        # from sgtk.platform.qt import QtCore, QtGui
        # class AliasEventFilter(QtCore.QObject):
        #     def eventFilter(self, obj, event):
        #         event_type = event.type()
        #         if event_type in (
        #             QtCore.QEvent.NonClientAreaMouseButtonDblClick,
        #             QtCore.QEvent.NonClientAreaMouseButtonPress,
        #             QtCore.QEvent.NonClientAreaMouseButtonRelease,
        #             # QtCore.QEvent.NonClientAreaMouseMove,
        #         ):
        #             print("===========================EVENT FILTER================================")
        #             print(f"\t{obj}")
        #             print(f"\t{event.type()}")
        #             print(f"\t{event.spontaneous()}")
        #         return super(AliasEventFilter, self).eventFilter(obj, event)
        # tk_alias_event_filter = AliasEventFilter()
        # qt_app = QtGui.QApplication.instance()
        # qt_app.installEventFilter(tk_alias_event_filter)

        if not self.sio:
            raise ClientNotFound("Alias client not found. Cannot send api request.")

        if not self.sio.connected:
            # TODO log warning
            raise ClientNotConnected(
                "Alias client is not connected. Cannot send api reqest."
            )
        
        # Sanitize functions - this cannot be done at time of encoding since we need access to
        # the client to store the callback function
        def __sanitize_arg(arg):
            if inspect.isfunction(arg) or inspect.ismethod(arg):
                if self.sio.has_callback(arg):
                    callback_id = self.sio.get_callback_id(arg)
                else:
                    callback_id = self.sio.set_callback(arg)
                return {"__callback_function_id__": callback_id}
            return arg

        if func_data:
            if "__function_args__" in func_data:
                args = []
                for arg in func_data.get("__function_args__", []):
                    args.append(__sanitize_arg(arg))
                func_data["__function_args__"] = args

            if "__function_kwargs__" in func_data:
                kwargs = {}
                for name, arg in func_data.get("__function_kwargs__", {}).items():
                    kwargs[name] = __sanitize_arg(arg)
                func_data["__function_kwargs__"] = kwargs


        def __send_request_async(event, data, namespace=None):
            # We need to emit non-blocking request and wait callback to set the result
            self.sio.emit_threadsafe(
                event,
                data,
                namespace=namespace,
                callback=__get_request_callback(response),
            )

            # Wait for server response, process any GUI events while waiting
            while not response.get("ack", False):
                # NOTE this resolve the issue with the UI freezing due to deadlock, but it does allow
                # user to interact with Alias during api calls (e.g. data validation)
                from sgtk.platform.qt import QtCore, QtGui

                qt_app = QtGui.QApplication.instance()
                event_dispatcher = qt_app.eventDispatcher()
                qt_app.processEvents(
                    QtCore.QEventLoop.ExcludeUserInputEvents
                    # | QtCore.QEventLoop.ExcludeSocketNotifiers
                    # | QtCore.QEventLoop.WaitForMoreEvents
                )

            return response.get("result")

        result = __send_request_async(func_name, func_data)

        # qt_app.removeEventFilter(tk_alias_event_filter)

        return result


class AliasClientModulePropertyProxy(AliasClientModuleAttributeProxy):
    """A proxy class to represent Alias API instance property."""

    def __init__(self, *args, **kwargs):
        """Initialize"""

        super(AliasClientModulePropertyProxy, self).__init__(*args, **kwargs)
        self.__property_name = args[0]["__property_name__"]

    @classmethod
    def needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set(["__property_name__"])
        value_keys = set(value)
        return required_keys.issubset(value_keys)

    def create_attribute(self, module, attribute_name):
        """
        """

        self.init(module, attribute_name)
        self.__property_name = attribute_name
        return self

    def __get__(self, instance, owner):
        """ """

        data = {
            "__instance_id__": instance.unique_id,
            "__property_name__": self.__property_name,
        }
        return self.send_request(self.__property_name, data)

    def __set__(self, instance, value):
        """ """

        data = {
            "__instance_id__": instance.unique_id,
            "__property_name__": self.__property_name,
            "__property_value__": value,
        }
        return self.send_request(self.__property_name, data)

    def __delete__(self, instance):
        # Not sure what to do here yet..
        pass


class AliasClientModuleFunctionProxy(AliasClientModuleAttributeProxy):
    """A proxy class to represnt an Alias API function."""

    def __init__(self, data=None):
        """Initialize the function proxy."""

        super(AliasClientModuleFunctionProxy, self).__init__(data=data)

        self.__func_name = data.get("__function_name__")
        self.__is_instance_method = data.get("__is_method__", False)

    @classmethod
    def needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set(["__function_name__"])
        value_keys = set(value.keys())
        return required_keys.issubset(value_keys)

    def create_attribute(self, module, attribute_name):
        self.init(module, attribute_name)
        return self.create_function()

    def create_function(self):
        if self.__is_instance_method:
            return self.__get_method()
        return self.__get_function()

    def __get_method(self):
        """Return a method."""

        def __method(instance, *args, **kwargs):
            """The attribute function."""

            data = {
                "__instance_id__": instance.unique_id,
                "__function_name__": self.__func_name,
                "__function_args__": args,
                "__function_kwargs__": kwargs,
            }
            return self.send_request(self.__func_name, data)

        return __method

    def __get_function(self):
        """Return a function."""

        def __function(*args, **kwargs):
            """The attribute function."""

            data = {
                "__function_name__": self.__func_name,
                "__function_args__": args,
                "__function_kwargs__": kwargs,
            }
            return self.send_request(self.__func_name, data)

        return __function


class AliasClientModuleClassProxy(AliasClientModuleAttributeProxy):
    """
    """

    @classmethod
    def needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set(
            [
                "__module_name__",
                "__class_name__",
                "__members__",
            ]
        )
        value_keys = set(value)
        return required_keys.issubset(value_keys)

    def create_attribute(self, module, attribute_name):
        """
        """

        self.init(module, attribute_name)

        class_members = self.data["__members__"]
        if class_members is None:
            # TODO look up class members? log warning?
            class_members = []

        class_type_name = self.data["__class_name__"]
        class_attrs = self._get_module_attributes(module, class_members)
        return type(class_type_name, (self.__class__,), class_attrs)


class AliasClientObjectProxy(AliasClientObjectProxyWrapper):
    """A proxy class to represent Alias objects."""

    @classmethod
    def needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set(
            [
                "__module_name__",
                "__class_name__",
                "__instance_id__",
            ]
        )
        value_keys = set(value.keys())
        return required_keys.issubset(value_keys)

    @classmethod
    def _create(cls, data):
        """ """

        proxy_module_name = data["__module_name__"]
        module = AliasClientObjectProxyWrapper.get_module(proxy_module_name)
        if not module:
            raise Exception("Module not found")

        proxy_type_name = data["__class_name__"]
        lookup_type = getattr(module, proxy_type_name)

        proxy_attributes = lookup_type.__dict__
        proxy_attributes = {
            k: v for k, v in proxy_attributes.items() if not k.startswith("__")
        }
        proxy_type = type(proxy_type_name, (cls,), proxy_attributes)

        # Return an actual instance of the proxy type, not just the type object (like other classes do)
        return proxy_type(data)

    @property
    def unique_id(self):
        """Return the unique id for this object."""
        return self.data["__instance_id__"]

class AliasClientModuleEnumProxy(AliasClientObjectProxy):
    """A proxy class to represent Alias API enums."""

    @classmethod
    def needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set(
            [
                "__class_name__",
                "__enum_name__",
                "__enum_value__",
            ]
        )
        value_keys = set(value)
        return required_keys.issubset(value_keys)

    @classmethod
    def _create(cls, data):
        """ """

        enum_class = data["__class_name__"]
        enum_name = data["__enum_name__"]
        enum_type_name = f"{enum_class}.{enum_name}"
        enum_attributes = {"name": enum_name, "value": data["__enum_value__"]}
        enum_type = type(enum_type_name, (cls,), enum_attributes)
        return enum_type(data)

