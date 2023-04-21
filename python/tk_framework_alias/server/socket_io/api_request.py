# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

from ..api import alias_api

from .. import alias_bridge
from ..utils.exceptions import AliasApiRequestNotValid


class AliasApiRequest:
    """Base abstract class to wrap data....."""

    @classmethod
    def create(cls, data):
        """Create and return a new object of this type from the given data, if possible."""

        if not isinstance(data, dict):
            return None

        for subclass in cls.__subclasses__():
            create_method = getattr(subclass, "_create")
            instance = create_method(data)
            if instance is not None:
                return instance

        return None

    @classmethod
    def _create(cls, data):
        """Create and return a new object of this type from the given data, if possible."""

        raise NotImplementedError("Subclass must implement")

    def validate(self, request_name):
        raise NotImplementedError("Subclass must implement")

    def execute(self, request_name):
        raise NotImplementedError("Subclass must implement")


class AliasFunction(AliasApiRequest):
    """A class to represent an Alias Python API module function call."""

    def __init__(self, func_name, func_args, func_kwargs, instance=None):
        """Initialize"""

        self.__instance = instance or alias_api
        self.__func_name = func_name
        self.__func_args = func_args
        self.__func_kwargs = func_kwargs

    @classmethod
    def _create(cls, data):
        """Create and return a new object of this type from the given data, if possible."""

        required_keys = set(
            [
                "__function_name__",
                "__function_args__",
                "__function_kwargs__",
            ]
        )

        if required_keys.issubset(set(data)):
            data_model = alias_bridge.AliasBridge().alias_data_model
            instance_id = data.get("__instance_id__")
            if instance_id:
                instance = data_model.get_instance(instance_id)
            else:
                instance = None
            return cls(
                data["__function_name__"],
                data["__function_args__"],
                data["__function_kwargs__"],
                instance=instance,
            )
        return None

    @property
    def instance(self):
        """Return None"""
        return self.__instance

    @property
    def func_name(self):
        """Get the args."""
        return self.__func_name

    @property
    def func_args(self):
        """Get the args."""
        return self.__func_args

    @property
    def func_kwargs(self):
        """Get the key-word arguments."""
        return self.__func_kwargs

    def validate(self, request_name):
        """Return True if the request is valid."""

        if request_name != self.__func_name:
            raise AliasApiRequestNotValid(
                f"Requested '{request_name}' but should be '{self.func_name}'"
            )

    def execute(self, request_name):
        """Execute the Alias Python API request."""

        self.validate(request_name)

        if self.func_name == "__new__":
            # NOTE pybind11 does not support calling cls.__new__(cls, args, kwargs)
            # until the python api is updated to provide a trampoline class to allow
            # calling __new__ method, we will just intercept this method and call the
            # constructor directly
            class_instance = self.func_args[0]
            args = self.func_args[1:]
            return class_instance(*args, *self.func_kwargs)
        else:
            # Get the Alias Python API method and execute it.
            method = getattr(self.instance, self.func_name)
            return method(*self.func_args, **self.func_kwargs)


class AliasInstanceProperty(AliasApiRequest):
    def __init__(self, instance, property_name):
        """Initialize"""

        self.__instance = instance
        self.__property_name = property_name

    @property
    def instance(self):
        """Get the id of the instance that this class corresponds to."""
        return self.__instance

    @property
    def property_name(self):
        """Get the id of the instance that this class corresponds to."""
        return self.__property_name

    @classmethod
    def _create(cls, data):
        """Create and return a new object of this type from the given data, if possible."""

        if not isinstance(data, dict):
            return None

        for subclass in cls.__subclasses__():
            create_method = getattr(subclass, "_create")
            instance = create_method(data)
            if instance is not None:
                return instance
        return None

    def validate(self, request_name):
        if request_name != self.property_name:
            raise AliasApiRequestNotValid(
                f"Requested '{request_name}' but should be '{self.property_name}'"
            )


class AliasInstancePropertyGetter(AliasInstanceProperty):
    """An Alias Python API property getter."""

    @classmethod
    def _create(cls, data):
        """Create and return a new object of this type from the given data, if possible."""

        required_keys = set(
            [
                "__instance_id__",
                "__property_name__",
            ]
        )

        if not required_keys.issubset(set(data)):
            return None

        if "__property_value__" in data:
            return None

        data_model = alias_bridge.AliasBridge().alias_data_model
        instance_id = data["__instance_id__"]
        instance = data_model.get_instance(instance_id)

        return cls(instance, data["__property_name__"])

    def execute(self, request_name):
        self.validate(request_name)
        return getattr(self.instance, self.property_name)


class AliasInstancePropertySetter(AliasInstanceProperty):
    def __init__(self, instance, property_name, property_value):
        """Initialize"""

        super(AliasInstancePropertySetter, self).__init__(instance, property_name)
        self.__property_value = property_value

    @property
    def property_value(self):
        """Get the id of the instance that this class corresponds to."""
        return self.__property_value

    @classmethod
    def _create(cls, data):
        """Create and return a new object of this type from the given data, if possible."""

        required_keys = set(
            ["__instance_id__", "__property_name__", "__property_value__"]
        )

        if not required_keys.issubset(set(data)):
            return None

        data_model = alias_bridge.AliasBridge().alias_data_model
        instance_id = data["__instance_id__"]
        instance = data_model.get_instance(instance_id)

        return cls(
            instance,
            data["__property_name__"],
            property_value=data["__property_value__"],
        )

    def execute(self, request_name):
        self.validate(request_name)
        setattr(self.instance, self.property_name, self.property_value)
