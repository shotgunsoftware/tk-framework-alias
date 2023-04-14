# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

import json
import inspect
import types
import importlib

from ..api import alias_api

from .. import alias_bridge
from .alias_api_request import AliasApiRequest
from .namespaces.alias_events_namespace import AliasEventsServerNamespace


class AliasServerJSON:
    """A custom json module to handle serializing Alias API objects to JSON."""

    @staticmethod
    def dumps(obj, *args, **kwargs):
        return json.dumps(obj, cls=AliasServerJSONEncoder, *args, **kwargs)

    @staticmethod
    def loads(obj, *args, **kwargs):
        return json.loads(obj, cls=AliasServerJSONDecoder, *args, **kwargs)


class AliasServerJSONEncoder(json.JSONEncoder):
    """A custom class to handle encoding Alis API objects."""

    def __init__(self, *args, **kwargs):
        """Initialize the encoder."""

        super(AliasServerJSONEncoder, self).__init__(*args, **kwargs)

    @staticmethod
    def is_al_object(obj):
        """Return True if the value is an Alias instance object."""

        module = getattr(obj, "__module__", None)
        return module == alias_api.__name__

    @staticmethod
    def is_al_enum(obj):
        """Return True if the object is an Alias Python API enum."""

        return (
            AliasServerJSONEncoder.is_al_object(obj) and
            hasattr(obj, "name") and
            hasattr(obj, "value") and
            hasattr(obj, "__entries")
        )

    @staticmethod
    def encode_exception(obj):
        """Encode an exception such that is JSON serializable."""

        # TODO improve this
        return {
            "exception_class": type(obj).__name__,
            "msg": str(obj),
            "traceback": obj.__traceback__,
        }

    @staticmethod
    def encode_set(obj):
        """Encode a set such that is JSON serializable."""

        # FIXME what if we need to konw this should be a set?
        return list(obj)
        # return {
        #     "__type__": set,
        #     "__value__": list(obj),
        # }

    @staticmethod
    def encode_property(obj):
        """Encode a property such that is JSON serializable."""

        return {
            "__property_name__": None,
        }

    @staticmethod
    def encode_descriptor(obj):
        """Encode a property such that is JSON serializable."""

        # TODO change this key name to descriptor__
        return {
            "__property_name__": obj.__name__,
        }

    @staticmethod
    def encode_callable(obj):
        """Encode a callable such that is JSON serializable."""

        # NOTE C-defined instance methods are not builtin functions or methods, so
        # this assumes if it is a callable but not a builtin function then it is an
        # instance method. The other option is to check the object class name is
        # "instancemethod"
        if obj.__class__.__name__ == "instancemethod":
            return AliasServerJSONEncoder.encode_method(obj)

        return AliasServerJSONEncoder.encode_function(obj)

    @staticmethod
    def encode_method(obj):
        """Encode a method such that is JSON serializable."""

        result = AliasServerJSONEncoder.encode_function(obj)
        result["__is_method__"] = True
        return result

    @staticmethod
    def encode_function(obj):
        """Encode a function such that is JSON serializable."""

        result = {
            "__function_name__": obj.__name__,
        }
        try:
            argspec = inspect.getfullargspec(obj)
            result["args"] = argspec.args
            result["varargs"] = argspec.varargs
            result["varkw"] = argspec.varkw
            result["defaults"] = argspec.defaults
            result["kwonlyargs"] = argspec.kwonlyargs
            result["kwonlydefaults"] = argspec.kwonlydefaults
            result["annotations"] = argspec.annotation
        except Exception:
            # Functions defined in C (e.g. pybind11 functions) are not supported by inspect,
            # only Python Functions. For C defined functions we cannot include the signature.
            pass
        
        return result

    def encode_class_type(self, obj):
        """Encode a class type object such that is JSON serializable."""

        class_type_name = obj.__name__
        members = inspect.getmembers(obj)

        class_members = []
        for member_name, member_value in members:
            if inspect.isclass(member_value):
                # Avoid circular references by not nesting class type objects.
                # Specify that this value is a class type but do not include its members, the
                # receiving end will need to look up the class type members from the root
                # module
                class_name = member_value.__name__
                value = {
                    "__module_name__": member_value.__module__,
                    "__class_name__": class_name,
                    "__members__": None,
                }
            else:
                value = member_value

            class_members.append((member_name, value))

        return {
            "__module_name__": obj.__module__,
            "__class_name__": class_type_name,
            "__members__": class_members,
        }

    @staticmethod
    def encode_al_enum(obj):
        """Encode an Alias Python API enum such that is JSON serializable."""

        return {
            "__module_name__": obj.__module__,
            "__class_name__": obj.__class__.__name__,
            "__enum_name__": obj.name,
            "__enum_value__": obj.value,
        }

    @staticmethod
    def encode_al_object(obj):
        """Encode an Alias Python API object such that is JSON serializable."""

        # NOTE think about the unique id...
        instance_id = id(obj)

        # Register the instance at encode time to ensure all encoded instances are registered
        # in the Alias Data Model.
        data_model = alias_bridge.AliasBridge().alias_data_model
        data_model.register_instance(instance_id, obj)

        return {
            "__module_name__": obj.__module__,
            "__class_name__": obj.__class__.__name__,
            "__instance_id__": instance_id,
        }

    def default(self, obj):
        """
        The default encode method.

        The order in which the type of the object is checked matters.
        """

        try: 
            if isinstance(obj, Exception):
                return self.encode_exception(obj)

            if isinstance(obj, property):
                return self.encode_property(obj)

            if isinstance(obj, set):
                return self.encode_set(obj)

            if isinstance(obj, types.MappingProxyType):
                return dict(obj)

            if isinstance(obj, importlib.machinery.ModuleSpec):
                return None

            if isinstance(obj, importlib.machinery.ExtensionFileLoader):
                return None

            if inspect.ismethod(obj):
                return self.encode_method(obj)

            if inspect.isfunction(obj):
                return self.encode_function(obj)

            if inspect.isgetsetdescriptor(obj):
                return self.encode_descriptor(obj)

            if inspect.ismemberdescriptor(obj):
                return self.encode_descriptor(obj)

            if inspect.isclass(obj):
                return self.encode_class_type(obj)

            if callable(obj):
                return self.encode_callable(obj)

            if self.is_al_enum(obj):
                return self.encode_al_enum(obj)

            if self.is_al_object(obj):
                return self.encode_al_object(obj)

            # Fall back to the default encode method.
            return super(AliasServerJSONEncoder, self).default(obj)

        except Exception as err:
            # Catch any errors and log an error message but do not fail the whole operation.
            # The value for this object will be set to None.
            print(f"AliasServerJSON Encoder Exception:")
            print(f"\t{err}")
            print(f"\t{obj}")
            # TODO log an error/warning
            return None
        

class AliasServerJSONDecoder(json.JSONDecoder):
    """A custom class to handle decoding Alias API objects."""

    def __init__(self, *args, **kwargs):
        """Initialize the decoder."""

        super(AliasServerJSONDecoder, self).__init__(object_hook=self.object_hook, *args, **kwargs)

    @staticmethod
    def create_callback(callback_id):
        def __handle_callback(*args, **kwargs):
            """Execute"""

            result = {
                "callback_event": callback_id,
                "args": args,
                "kwargs": kwargs,
            }

            # Emit event, from the Alias event client socket, to the server it is connected to
            # The server will then handle emitting the event to other clients that care about
            # this Alias event.
            sio.emit(
                "alias_event_callback",
                data=result,
                namespace=AliasEventsServerNamespace.get_namespace()
            )

        # Set the sio for when the callback is triggered. Emit the event from the Alias events
        # client socketio to the server, since the server cannot directly handle the event from
        # Alias because it is in a separate thread.
        sio = alias_bridge.AliasBridge().alias_events_client_sio
        return __handle_callback

    def object_hook(self, obj):
        """Decode an object."""

        # First, try to decode the object into an Alias API request object.
        alias_data = AliasApiRequest.create(obj)
        if alias_data is not None:
            return alias_data

        if isinstance(obj, dict):
            # Next, try to decode the object as an Alias instance
            instance_id = obj.get("__instance_id__")
            if instance_id is not None:
                data_model = alias_bridge.AliasBridge().alias_data_model

                # NOTE should we have some validation that the registry had the instance id?
                return data_model.get_instance(instance_id)

            # Next, try to decode the object as an Alias class object
            if "__class_name__" in obj:
                class_name = obj["__class_name__"]
                class_obj = getattr(alias_api, class_name)

                # Try to decode as enum class first
                if "__enum_name__" in obj:
                    return getattr(class_obj, obj["__enum_name__"])

                return class_obj

            # Next, try to decode as a callback function
            if "__callback_function_id__" in obj:
                return self.create_callback(obj["__callback_function_id__"])

            # Next, try to decode a set
            if "__set__" in obj:
                return set(obj["__set__"])

        # Just return the object as is
        return obj
