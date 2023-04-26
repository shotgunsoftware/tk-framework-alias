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
import json

from .proxy_wrapper import AliasClientObjectProxyWrapper
from .exceptions import AliasClientJSONEncoderError


class AliasClientJSON:
    """A custom json module to handle serializing Alias API objects."""

    @staticmethod
    def encoder_class():
        return AliasClientJSONEncoder

    @staticmethod
    def decoder_class():
        return AliasClientJSONDecoder

    @staticmethod
    def dumps(obj, *args, **kwargs):
        return json.dumps(obj, cls=AliasClientJSON.encoder_class(), *args, **kwargs)

    @staticmethod
    def loads(obj, *args, **kwargs):
        return json.loads(obj, cls=AliasClientJSON.decoder_class(), *args, **kwargs)


class AliasClientJSONEncoder(json.JSONEncoder):
    """A custom class to handle encoding Alias API objects."""

    def __init__(self, *args, **kwargs):
        """Initialize the encoder."""

        super(AliasClientJSONEncoder, self).__init__(*args, **kwargs)

    def default(self, obj):
        """Encode the object."""

        if isinstance(obj, AliasClientObjectProxyWrapper):
            return obj.sanitize()

        if isinstance(obj, set):
            return {"__set__": list(obj)}

        if inspect.isclass(obj):
            return {"__class_name__": obj.__name__}

        if inspect.isfunction(obj) or inspect.ismethod(obj):
            # Functions must be registered in the AliasSocketIoClient. Since the client io
            # cannot be accessed here, functions must be encoded before getting to this stage.
            raise AliasClientJSONEncoderError("Functions should already be encoded.")

        return super(AliasClientJSONEncoder, self).default(obj)


class AliasClientJSONDecoder(json.JSONDecoder):
    """A custom class to handle decoding Alias API objects."""

    def __init__(self, *args, **kwargs):
        """Initialize the decoder."""

        super(AliasClientJSONDecoder, self).__init__(
            object_hook=self.object_hook, *args, **kwargs
        )

    def object_hook(self, obj):
        """Decode the object."""

        if isinstance(obj, dict):
            if "exception_class" in obj:
                exception_class_name = obj["exception_class"]
                exception_class = type(exception_class_name, (Exception,), {})
                exception_instance = exception_class(
                    obj.get("msg", "Alias Python API error")
                )
                return exception_instance

            if isinstance(obj.get("__type__"), set):
                return set(obj.get("__value__"))

        proxy_obj = AliasClientObjectProxyWrapper.create_proxy(obj)
        if proxy_obj is not None:
            return proxy_obj

        return obj
