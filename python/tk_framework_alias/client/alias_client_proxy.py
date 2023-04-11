# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import threading
import types


class AliasClientModuleProxy():
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

        required_keys = set([
            "__module_name__",
            "__members__",
        ])
        value_keys = set(value)
        # return required_keys.issubset(value_keys)
        return required_keys == value_keys

    def _get_attributes(self, members):
        """Return an attributes dictionary from the member data."""

        if not members:
            return  {}

        attrs = {}
        for member_name, member_value in members:
            if isinstance(member_value, AliasClientProxy):
                attrs[member_name] = member_value.create_attribute(member_name, self.__sio)
            else:
                attrs[member_name] = member_value
            
        return attrs

    def sanitize(self):
        return self.__data

    def get_or_create_module(self, sio):

        # module_name = data["__module_name__"]
        # module_attrs = cls._get_attributes(data["__members__"])
        # This creates a class type object
        # return type(module_name, (cls,), module_attrs)
        # import importlib.util
        # module_spec = importlib.util.spec_from_loader(module_name, loader=None)
        # module = importlib.util.module_from_spec(module_spec)

        self.__sio = sio

        if self.module_name in self.__modules:
            return self.__modules[self.module_name]

        module = types.ModuleType(self.module_name)

        module_attrs = self._get_attributes(self.__data["__members__"])
        module.__dict__.update(module_attrs)

        # Store the module in the class list of modules
        self.__modules[self.module_name] = module

        return module


class AliasClientProxy():
    """The base abstract proxy class to represent Alias API objects."""

    def __init__(self, data=None):
        """Initialize the proxy."""

        self.__data = data or {}
        self.__unique_id = self.__data.get("__instance_id__")

        self._sio = None

    @classmethod
    def create_proxy(cls, data):
        """Factory method to create an AliasClientProxy object."""

        if not isinstance(data, dict):
            return None

        for subclass in cls.__subclasses__():
            if getattr(subclass, "_needs_wrapping")(data):
                return subclass._create(data)
                # return subclass(data)
        
        return None

    @classmethod
    def needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by an AliasClientProxy (sub)class."""

        if not isinstance(value, dict):
            return False

        for subclass in cls.__subclasses__():
            if getattr(subclass, "_needs_wrapping")(value):
                return True

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

    def create_attribute(self, attribute_name, sio):
        """
        """

        # raise NotImplementedError("Subclass must implement")
        self._sio = sio
        return self

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

    def _get_attributes(self, members):
        """Return an attributes dictionary from the member data."""

        attrs = {}

        for member_name, member_value in members:
            if isinstance(member_value, AliasClientProxy):
                attrs[member_name] = member_value.create_attribute(member_name, self._sio)
            else:
                attrs[member_name] = member_value
            
        return attrs

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




        from sgtk.platform.qt import QtCore, QtGui
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




        if not self._sio:
            print("NO SIO - abort request......")
            return

        # async def __send_request_async(event, data, namespace):
        def __send_request_async(event, data, namespace=None):
            # We need to emit non-blocking request and wait callback to set the result
            # self.__sio.emit_threadsafe(
            self._sio.emit_threadsafe(
                event,
                data,
                namespace=namespace,
                callback=__get_request_callback(response)
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
                # # sio.sleep(0.1)
                # await asyncio.sleep(0.1)

            return response.get("result")

        # Running in asyncio makes it very slow...
        # import asyncio 
        # result = asyncio.run(__send_request_async(func_name, func_data, sio.shotgrid_namespace))

        result = __send_request_async(func_name, func_data)
        # result = __send_request_async(func_name, func_data, sio.shotgrid_namespace)
        # print(f"\tResult: {result}")

        # qt_app.removeEventFilter(tk_alias_event_filter)

        return result



class AliasClientClassTypeProxy(AliasClientProxy):

    @classmethod
    def _needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set([
            "__module_name__",
            "__class_name__",
            "__members__",
        ])
        value_keys = set(value)
        return required_keys.issubset(value_keys)

    def create_attribute(self, attribute_name, sio):
        self._sio = sio
        return self.create_class_type()

    def create_class_type(self):
        """Factory method to create a subclass of AliasClientClassTypeProxy."""

        class_members = self.data["__members__"]

        if class_members is None:
            # TODO look up class members? log warning?
            class_members = []

        class_type_name = self.data["__class_name__"]
        class_attrs = self._get_attributes(class_members)
        return type(class_type_name, (AliasClientClassTypeProxy,), class_attrs)


class AliasClientPropertyProxy(AliasClientProxy):
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

    def create_attribute(self, attribute_name, sio):
        self._sio = sio
        self.set_name(attribute_name)
        return self

    def set_name(self, name):
        self.__property_name = name

    def __get__(self, instance, owner):
        """
        """

        data = {
            "__instance_id__": instance.unique_id,
            "__property_name__": self.__property_name,
        }
        return self.send_request(self.__property_name, data)

    def __set__(self, instance, value):
        """
        """

        data = {
            "__instance_id__": instance.unique_id,
            "__property_name__": self.__property_name,
            "__property_value__": value,
        }
        return self.send_request(self.__property_name, data)

    def __delete__(self, instance):
        # Not sure what to do here yet..
        pass


class AliasClientEnumProxy(AliasClientProxy):
    """A proxy class to represent Alias API enums."""

    @classmethod
    def _needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set([
            "__class_name__",
            "__enum_name__",
            "__enum_value__",
        ])
        value_keys = set(value)
        return required_keys.issubset(value_keys)
    
    @classmethod
    def _create(cls, data):
        """
        """

        enum_class = data["__class_name__"]
        enum_name = data["__enum_name__"]
        enum_type_name = f"{enum_class}.{enum_name}"
        enum_attributes = {
            "name": enum_name,
            "value": data["__enum_value__"]
        }

        enum_type = type(enum_type_name, (cls, ), enum_attributes)
        return enum_type(data)


class AliasClientObjectProxy(AliasClientProxy):
    """A proxy class to represent Alias API objects."""

    @classmethod
    def _needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set([
            "__module_name__",
            "__class_name__",
            "__instance_id__",
        ])
        value_keys = set(value.keys())
        return required_keys.issubset(value_keys)

    @classmethod
    def _create(cls, data):
        """
        """

        proxy_module_name = data["__module_name__"]
        module = AliasClientModuleProxy.get_module(proxy_module_name)
        if not module:
            raise Exception("Module not found")

        proxy_type_name = data["__class_name__"]
        lookup_type = getattr(module, proxy_type_name)

        proxy_attributes = lookup_type.__dict__
        proxy_attributes = {k:v for k, v in proxy_attributes.items() if not k.startswith("__")}
        proxy_type = type(proxy_type_name, (cls,), proxy_attributes)

        # Return an actual instance of the proxy type, not just the type object (like other classes do)
        return proxy_type(data)


class AliasClientFunctionProxy(AliasClientProxy):
    """A proxy class to represnt an Alias API function."""

    def __init__(self, data=None):
        """Initialize the function proxy."""

        super(AliasClientFunctionProxy, self).__init__(data=data)

        self.__func_name = data.get("__function_name__")
        self.__is_instance_method = data.get("__is_method__", False)


    @classmethod
    def _needs_wrapping(cls, value):
        """Return True if the value represents an object that needs to be wrapped by this proxy class."""

        required_keys = set(["__function_name__"])
        value_keys = set(value.keys())
        return required_keys.issubset(value_keys)

    def create_attribute(self, attribute_name, sio):
        self._sio = sio
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

