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
import traceback

from ..api import alias_api

from .. import alias_bridge
from .api_request import AliasApiRequestWrapper
from .namespaces.events_namespace import AliasEventsServerNamespace
from ..utils.exceptions import AliasServerJSONDecoderError


class AliasServerJSON:
    """A custom json module to handle serializing Alias API objects to JSON."""

    @staticmethod
    def encoder_class():
        """Return the encoder class used by this JSON module."""
        return AliasServerJSONEncoder

    @staticmethod
    def decoder_class():
        """Return the decoder class used by this JSON module."""
        return AliasServerJSONDecoder

    @staticmethod
    def dumps(obj, *args, **kwargs):
        return json.dumps(obj, cls=AliasServerJSON.encoder_class(), *args, **kwargs)

    @staticmethod
    def loads(obj, *args, **kwargs):
        return json.loads(obj, cls=AliasServerJSON.decoder_class(), *args, **kwargs)


class AliasServerJSONEncoder(json.JSONEncoder):
    """A custom class to handle encoding Alias API objects."""

    def __init__(self, *args, **kwargs):
        """Initialize the encoder."""

        # Disable the built-in circular reference check; we handle cycle prevention
        # ourselves via _seen_ids in encode_class_type/encode_module.
        kwargs["check_circular"] = False
        super().__init__(*args, **kwargs)
        self._seen_ids = set()
        self._module_cache_mode = False

    @staticmethod
    def is_al_object(obj):
        """Return True if the value is an Alias instance object."""

        module = getattr(obj, "__module__", None)
        return module == alias_api.__name__

    @staticmethod
    def is_al_enum(obj):
        """Return True if the object is an Alias Python API enum."""

        if not AliasServerJSONEncoder.is_al_object(obj):
            return False
        if inspect.isclass(obj):
            return False
        # pybind11 enum classes expose a __members__ mapping (name -> value)
        # or __entries dict depending on version. Check the class for either.
        obj_type = type(obj)
        if hasattr(obj_type, "__entries"):
            return True
        # Check multiple ways — pybind11 types may use custom descriptors
        if "__members__" in dir(obj_type):
            try:
                pb11_members = getattr(obj_type, "__members__", None)
                if pb11_members is not None and hasattr(pb11_members, "items"):
                    return True
            except Exception:
                pass
        # Last resort: pybind11 arithmetic enums support int conversion
        try:
            int(obj)
            # Verify it's not just a regular numeric Alias object — check if
            # repr looks like an enum: <ClassName.Name: value>
            r = repr(obj)
            if r.startswith("<") and "." in r and ":" in r:
                return True
        except (TypeError, ValueError):
            pass
        return False

    @staticmethod
    def encode_exception(obj):
        """Encode an exception such that is JSON serializable."""

        return {
            "__exception_class_name__": type(obj).__name__,
            "__msg__": str(obj),
            "__traceback__": obj.__traceback__,
        }

    @staticmethod
    def encode_set(obj):
        """Encode a set such that is JSON serializable."""

        return {
            "__type__": "set",
            "__value__": list(obj),
        }

    @staticmethod
    def encode_property(obj):
        """Encode a property such that is JSON serializable."""

        return {
            "__property_name__": None,
        }

    @staticmethod
    def encode_descriptor(obj):
        """Encode a property such that is JSON serializable."""

        # NOTE descriptors are handled like properties for now. This might need to be updated
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
            return AliasServerJSONEncoder.encode_function(obj, is_method=True)

        return AliasServerJSONEncoder.encode_function(obj)

    @staticmethod
    def is_unbound_method(obj):
        """Check if a function is an unbound method (defined within a class)."""

        if not inspect.isfunction(obj):
            return False

        # Check if the function has a qualified name indicating it's from a class
        if hasattr(obj, "__qualname__") and "." in obj.__qualname__:
            return True

        return False

    @staticmethod
    def encode_function(obj, is_method=False):
        """Encode a function such that is JSON serializable."""

        return {
            "__function_name__": obj.__name__,
            "__is_method__": is_method,
        }

    @staticmethod
    def _sanitize_dict_keys(obj, _seen=None):
        """Convert dict keys that are not JSON-serializable to their string representation.

        The json encoder's ``default`` method only handles values; dict keys that are not
        str/int/float/bool/None cause a TypeError before ``default`` is ever called. This
        handles dicts found in pybind11 modules (e.g. ``__entries__``) that use type objects
        as keys.
        """

        if not isinstance(obj, (dict, list, tuple)):
            return obj

        if _seen is None:
            _seen = set()

        obj_id = id(obj)
        if obj_id in _seen:
            return None
        _seen.add(obj_id)

        if isinstance(obj, dict):
            sanitized = {}
            for k, v in obj.items():
                if not isinstance(k, (str, int, float, bool, type(None))):
                    k = str(k)
                sanitized[k] = AliasServerJSONEncoder._sanitize_dict_keys(v, _seen)
            _seen.discard(obj_id)
            return sanitized

        result = type(obj)(
            AliasServerJSONEncoder._sanitize_dict_keys(item, _seen) for item in obj
        )
        _seen.discard(obj_id)
        return result

    def _encode_member_value(self, member_value):
        """Encode a member value for use in module/class member lists.

        Handles Alias API instances and enums as lightweight references so they
        don't trigger client-side proxy creation during cache deserialization
        (which fails because the module hasn't been registered yet at that point).

        Order matters: callables must be checked before is_al_object because
        pybind11 methods have __module__ set to the API module name.
        """

        if inspect.isclass(member_value):
            return {
                "__module_name__": member_value.__module__,
                "__class_name__": member_value.__name__,
                "__members__": None,
            }
        if inspect.ismodule(member_value):
            return {"__module_name__": member_value.__name__}
        if self.is_al_enum(member_value):
            return self.encode_al_enum(member_value)
        if callable(member_value):
            return self.encode_callable(member_value)
        if self.is_al_object(member_value):
            return {
                "__module_name__": member_value.__module__,
                "__class_name__": member_value.__class__.__name__,
                "__al_instance_repr__": repr(member_value),
            }
        return self._sanitize_dict_keys(member_value)

    def encode_class_type(self, obj):
        """Encode a class type object such that is JSON serializable."""

        obj_id = id(obj)
        if obj_id in self._seen_ids:
            return {
                "__module_name__": obj.__module__,
                "__class_name__": obj.__name__,
                "__members__": None,
            }
        self._seen_ids.add(obj_id)

        class_type_name = obj.__name__
        members = inspect.getmembers(obj)

        # pybind11 enum classes may not expose all enum values in dir(), so
        # inspect.getmembers misses them. Look for a __members__ mapping in the
        # already-retrieved members (maps name -> enum value/int).
        existing_names = {m[0] for m in members}
        pb11_dict = None
        for member_name, member_value in list(members):
            if member_name == "__members__":
                pb11_dict = member_value
                break
        if pb11_dict is None:
            # Try direct attribute access as fallback
            try:
                pb11_dict = getattr(obj, "__members__", None)
            except Exception:
                pass
        if pb11_dict is not None:
            try:
                items = pb11_dict.items() if hasattr(pb11_dict, "items") else []
                for name, value in items:
                    if name not in existing_names:
                        members.append((name, value))
                        existing_names.add(name)
            except Exception:
                pass

        class_members = []
        for member_name, member_value in members:
            class_members.append((member_name, self._encode_member_value(member_value)))

        return {
            "__module_name__": obj.__module__,
            "__class_name__": class_type_name,
            "__members__": class_members,
        }

    def encode_module(self, obj):
        """Encode a module object such that is JSON serializable."""

        obj_id = id(obj)
        if obj_id in self._seen_ids:
            return {"__module_name__": obj.__name__}
        self._seen_ids.add(obj_id)
        self._module_cache_mode = True

        members = []
        for name, value in inspect.getmembers(obj):
            if inspect.isclass(value):
                # Let classes pass through so the encoder calls encode_class_type
                # with full member data (unlike _encode_member_value which stubs them)
                members.append((name, value))
            elif inspect.ismodule(value):
                members.append((name, {"__module_name__": value.__name__}))
            elif self.is_al_enum(value):
                members.append((name, self.encode_al_enum(value)))
            elif callable(value):
                members.append((name, self.encode_callable(value)))
            elif self.is_al_object(value):
                members.append(
                    (
                        name,
                        {
                            "__module_name__": value.__module__,
                            "__class_name__": value.__class__.__name__,
                            "__al_instance_repr__": repr(value),
                        },
                    )
                )
            else:
                members.append((name, self._sanitize_dict_keys(value)))

        return {
            "__module_name__": obj.__name__,
            "__members__": members,
        }

    @staticmethod
    def encode_al_enum(obj):
        """Encode an Alias Python API enum such that is JSON serializable."""

        obj_type = type(obj)
        # Try direct .name/.value first; fall back to __members__ reverse
        # lookup and int() for pybind11 arithmetic enums where the properties
        # may not be accessible on instances.
        enum_name = None
        enum_value = None
        try:
            enum_name = obj.name
        except (AttributeError, TypeError):
            pass
        try:
            enum_value = obj.value
        except (AttributeError, TypeError):
            pass

        if enum_name is None:
            try:
                pb11_members = getattr(obj_type, "__members__", None)
                if pb11_members and hasattr(pb11_members, "items"):
                    for member_name, member_value in pb11_members.items():
                        if member_value == obj:
                            enum_name = member_name
                            break
            except Exception:
                pass

        if enum_name is None:
            # Parse from repr: "<ClassName.EnumName: value>"
            try:
                r = repr(obj)
                if "." in r and ":" in r:
                    enum_name = r.split(".")[1].split(":")[0].strip()
            except Exception:
                pass

        if enum_value is None:
            try:
                enum_value = int(obj)
            except (TypeError, ValueError):
                enum_value = 0

        return {
            "__module_name__": getattr(obj, "__module__", obj_type.__module__),
            "__class_name__": obj_type.__name__,
            "__enum_name__": enum_name,
            "__enum_value__": enum_value,
        }

    @staticmethod
    def encode_al_object(obj):
        """Encode an Alias Python API object such that is JSON serializable."""

        # Register the instance at encode time to ensure all encoded instances are registered
        # in the Alias Data Model.
        data_model = alias_bridge.AliasBridge().alias_data_model
        instance_id = data_model.register_instance(obj)

        return {
            "__module_name__": obj.__module__,
            "__class_name__": obj.__class__.__name__,
            "__instance_id__": instance_id,
            "__dict__": {
                "name": obj.name if hasattr(obj, "name") else None,
                "type": obj.type() if hasattr(obj, "type") else None,
            },
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
                return self._sanitize_dict_keys(dict(obj))

            if isinstance(obj, importlib.machinery.ModuleSpec):
                return None

            if isinstance(obj, importlib.machinery.ExtensionFileLoader):
                return None

            if inspect.istraceback(obj):
                result = traceback.format_tb(obj)
                return result

            if inspect.ismethod(obj):
                return self.encode_function(obj, is_method=True)

            if self.is_unbound_method(obj):
                # If the function is an unbound method, encode it as a method.
                return self.encode_function(obj, is_method=True)

            if inspect.isfunction(obj):
                return self.encode_function(obj)

            if inspect.isgetsetdescriptor(obj):
                return self.encode_descriptor(obj)

            if inspect.ismemberdescriptor(obj):
                return self.encode_descriptor(obj)

            if inspect.isclass(obj):
                return self.encode_class_type(obj)

            if inspect.ismodule(obj):
                return self.encode_module(obj)

            if self.is_al_enum(obj):
                return self.encode_al_enum(obj)

            if callable(obj):
                return self.encode_callable(obj)

            if self.is_al_object(obj):
                if self._module_cache_mode:
                    return {
                        "__module_name__": obj.__module__,
                        "__class_name__": obj.__class__.__name__,
                        "__al_instance_repr__": repr(obj),
                    }
                return self.encode_al_object(obj)

            # Handle opaque C objects (PyCapsule, etc.) returned by Alias API
            # by registering them in the data model so the client gets a ref ID.
            if type(obj).__name__ == "PyCapsule":
                data_model = alias_bridge.AliasBridge().alias_data_model
                instance_id = data_model.register_instance(obj)
                return {
                    "__module_name__": alias_api.__name__,
                    "__class_name__": "PyCapsule",
                    "__instance_id__": instance_id,
                    "__dict__": {"name": None, "type": None},
                }

            # Fall back to the default encode method.
            return super().default(obj)

        except Exception as encode_error:
            # Catch any errors from encoding and return the exception encoded.
            return self.encode_exception(encode_error)


class AliasServerJSONDecoder(json.JSONDecoder):
    """A custom class to handle decoding Alias API objects."""

    def __init__(self, *args, **kwargs):
        """Initialize the decoder."""

        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    @staticmethod
    def create_callback(callback_id):
        """
        Create a function to handle an Alias

        This function can be passed to the Alias C++ API, which when triggered, will forward
        a socketio event to the client, to execute the actual callback function (that lives on
        the client side). This is required since functions cannot be passed directly between
        the socketio server and client.

        NOTE this assume only one client is connected to the server. To support multiple
        clients, the client sid must be stored with the callback data to know which client
        to send the event to.
        """

        def __handle_callback(*args, **kwargs):
            """Execute the callback"""

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
                namespace=AliasEventsServerNamespace.get_namespace(),
            )

        # Set the sio for when the callback is triggered. Emit the event from the Alias events
        # client socketio to the server, since the server cannot directly handle the event from
        # Alias because it is in a separate thread.
        sio = alias_bridge.AliasBridge().alias_events_client_sio
        return __handle_callback

    def object_hook(self, obj):
        """Decode an object."""

        # First, try to decode the object into an Alias API request object.
        request = AliasApiRequestWrapper.create_wrapper(obj)
        if request is not None:
            return request

        if isinstance(obj, dict):
            # Next, try to decode the object as an Alias instance
            instance_id = obj.get("__instance_id__")
            if instance_id is not None:
                data_model = alias_bridge.AliasBridge().alias_data_model
                instance = data_model.get_instance(instance_id)
                if instance is None:
                    raise AliasServerJSONDecoderError(
                        "Instance not found in data model registry"
                    )
                return instance

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
            if "__type__" in obj:
                if obj["__type__"] == "set":
                    return set(obj["__value__"])

        # Just return the object as is
        return obj
