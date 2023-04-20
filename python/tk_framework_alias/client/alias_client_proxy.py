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


class AliasClientModuleProxy:
    """A proxy class to represent an Alias Python API module."""

    __modules = {}
    __module_lock = threading.Lock()

    def __init__(self, module_data):
        """Initialize"""

        self.__data = module_data
        self.__sio = None

        self.module_name = self.__data["__module_name__"]

    @classmethod
    def get_module(cls, module_name):
        """Return the module for the given name."""

        with cls.__module_lock:
            return cls.__modules.get(module_name)

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

    def sanitize(self):
        return self.__data

    def _get_attributes(self, members):
        """Return an attributes dictionary from the member data."""

        if not members:
            return {}

        attrs = {}
        for member_name, member_object in members:
            if isinstance(member_object, AliasClientModuleProxyAttribute):
                # attrs[member_name] = member_value.create_attribute(
                #     member_name, self.__sio
                # )
                member_object.init(self, member_name)

            elif inspect.isclass(member_object) and issubclass(member_object, AliasClientModuleProxyAttribute):
                member_object.init_class(self, member_name)

            attrs[member_name] = member_object

        return attrs

    def get_or_create_module(self, sio):
        """Get or create the module."""

        self.__sio = sio

        with self.__module_lock:
            # Check if the module has already been created.
            if self.module_name in self.__modules:
                return self.__modules[self.module_name]

            # Create the new module
            module = types.ModuleType(self.module_name)

            # Get and set the module attributes dictionary
            module_attrs = self._get_attributes(self.__data["__members__"])
            module.__dict__.update(module_attrs)

            # Store the module in the class list of modules
            self.__modules[self.module_name] = module

            return module


class AliasClientModuleProxyAttribute:
    """The base abstract proxy class to represent Alias API objects."""

    def __init__(self, data=None):
        """Initialize the proxy."""

        self.__data = data or {}
        self.__unique_id = self.__data.get("__instance_id__")

        self.__module = None

    @classmethod
    def create_proxy(cls, data):
        """Factory method to create an AliasClientModuleProxyAttribute object."""

        if not isinstance(data, dict):
            return None

        for subclass in cls.__subclasses__():
            if getattr(subclass, "_needs_wrapping")(data):
                return subclass._create(data)

        return None

    @classmethod
    def needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by an AliasClientModuleProxyAttribute (sub)class."""

        if not isinstance(value, dict):
            return False

        for subclass in cls.__subclasses__():
            if getattr(subclass, "_needs_wrapping")(value):
                return True

    @property
    def module(self):
        """Get the module this attribute belogns to."""
        return self.__module

    @property
    def sio(self):
        """Get the socketio client to communicate with Alias."""
        return self.__module.sio

    @property
    def unique_id(self):
        """Get the unique id for this proxy wrapper object."""
        return self.__unique_id

    @property
    def data(self):
        """Get the original data that created this proxy wrapper object."""
        return self.__data

    # Abstract methods must be implemented by subclass
    # ----------------------------------------------------------------------------------------

    def init(self, module, attribute_name):
        """
        Initialize the attribute.
        
        This must be called before the module attribute is used.

        Set the module that this attribute belongs to.
        """

        self.__module = module

    # def create_attribute(self, attribute_name, module):
    #     """ """
    #     self.__module = module
    #     self._sio = self.__module.sio
    #     return self

    def _needs_wrapping(self, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        raise NotImplementedError("Subclass must implement")

    @classmethod
    def _create(cls, data):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        return cls(data)

    def sanitize(self):
        """Return a sanitized representation of this proxy that is JSON serializable."""

        return self.data

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



class AliasClientPropertyProxy(AliasClientModuleProxyAttribute):
    """A proxy class to represent Alias API instance property."""

    def __init__(self, *args, **kwargs):
        super(AliasClientPropertyProxy, self).__init__(*args, **kwargs)
        self.__property_name = args[0]["__property_name__"]

    @classmethod
    def _needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set(["__property_name__"])
        value_keys = set(value)
        return required_keys.issubset(value_keys)

    def init(self, module, attribute_name):
        """
        """

        super(AliasClientPropertyProxy, self).init(module, attribute_name)
        self.set_name(attribute_name)

    # def create_attribute(self, attribute_name, sio):
    #     self._sio = sio
    #     self.set_name(attribute_name)
    #     return self

    def set_name(self, name):
        self.__property_name = name

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


class AliasClientEnumProxy(AliasClientModuleProxyAttribute):
    """A proxy class to represent Alias API enums."""

    @classmethod
    def _needs_wrapping(cls, value):
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


class AliasClientObjectProxy(AliasClientModuleProxyAttribute):
    """A proxy class to represent Alias API objects."""

    @classmethod
    def _needs_wrapping(cls, value):
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
        module = AliasClientModuleProxy.get_module(proxy_module_name)
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

    def __getattribute__(self, __name):
        attr = super().__getattribute__(__name)
        if isinstance(attr, AliasClientFunctionProxy):
            attr.set_instance(self)
        return attr


class AliasClientFunctionProxy(AliasClientModuleProxyAttribute):
    """A proxy class to represnt an Alias API function."""

    def __init__(self, data=None):
        """Initialize the function proxy."""

        super(AliasClientFunctionProxy, self).__init__(data=data)

        self.__func_name = data.get("__function_name__")
        self.__is_instance_method = data.get("__is_method__", False)
        self.__instance = None

    @classmethod
    def _needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set(["__function_name__"])
        value_keys = set(value.keys())
        return required_keys.issubset(value_keys)

    def __call__(self, *args, **kwargs):
        """ """
        func = self.create_function()
        return func(*args, **kwargs)

    def set_instance(self, instance):
        self.__instance = instance

    def create_function(self):
        if self.__is_instance_method:
            return self.__get_method()
        return self.__get_function()

    def __get_method(self):
        """Return a method."""

        # def __method(instance, *args, **kwargs):
        def __method(*args, **kwargs):
            """The attribute function."""

            data = {
                # "__instance_id__": instance.unique_id,
                "__instance_id__": self.__instance.unique_id,
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

# FIXME this is a class type object - how does this fit in better...
class AliasClientClassTypeProxy(AliasClientModuleProxyAttribute):
    """
    """

    __class_data = {}
    __classes_lock = threading.Lock()

    @classmethod
    def _needs_wrapping(cls, value):
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

    @classmethod
    def init_class(cls, module, attribute_name):
        """Initialize the attribute for the given module."""

        # Initialize the class members for the module
        for member_name, member_value in cls.__dict__.items():
            if isinstance(member_value, AliasClientModuleProxyAttribute):
                member_value.init(module, member_name)

    @classmethod
    def sanitize_class(cls):
        """Sanitize the class."""

        class_type_name = cls.__name__
        with cls.__classes_lock:
            return cls.__class_data.get(class_type_name)

    @classmethod
    def _create(cls, data):
        """Factory method to create a subclass of AliasClientClassTypeProxy."""

        class_members = data["__members__"]

        if class_members is None:
            # TODO look up class members? log warning?
            class_members = []

        class_type_name = data["__class_name__"]
        class_attrs = {}
        for member_name, member_value in class_members:
            class_attrs[member_name] = member_value

        # Store the class data
        with cls.__classes_lock:
            cls.__class_data[class_type_name] = data

        # NOTE this is return a class type object, not an instance
        return type(class_type_name, (AliasClientClassTypeProxy,), class_attrs)
        # return type(class_type_name, (cls,), class_attrs)
