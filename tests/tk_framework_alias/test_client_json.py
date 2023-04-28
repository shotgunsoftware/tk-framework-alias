# Copyright (c) 2021 Autoiesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

import pytest

from tk_framework_alias.client.socketio import client_json
from tk_framework_alias.client.socketio import proxy_wrapper
from tk_framework_alias.client.utils.exceptions import AliasClientJSONEncoderError



####################################################################################################
# fixtures
####################################################################################################

@pytest.fixture(autouse=True)
def json_encoder():
    """Fixture to return an instance of the AliasClientJSONEncoder class."""

    return client_json.AliasClientJSONEncoder()

@pytest.fixture(autouse=True)
def json_decoder():
    """Fixture to return an instance of the AliasClientJSONDecoder class."""

    return client_json.AliasClientJSONDecoder()


####################################################################################################
# tk_framework_alias client_json AliasClientJSONEncoder
####################################################################################################

@pytest.mark.parametrize(
    "value",
    [
        (set()),
        (set({1})),
        (set({1, 2, 3})),
        (set({"1", "2", "2"})),
        ({1}),
        ({1, 2, 3}),
        ({"1", "2", "2"}),
    ],
)
def test_json_encode_set(json_encoder, value):
    """Test the AliasClientJSONEncoder default method to encode set objects."""

    result = json_encoder.default(value)
    expected = {
        "__type__": set,
        "__value__": list(value)
    }
    assert result == expected

def test_json_encode_function(json_encoder):
    """Test the AliasClientJSONEncoder default method to encode function objects."""

    def my_func():
        pass

    with pytest.raises(AliasClientJSONEncoderError):
        json_encoder.default(my_func)

def test_json_encode_class_type(json_encoder):
    """Test the AliasClientJSONEncoder default method to encode class objects."""

    class MyClassToEncode:
        pass

    result = json_encoder.default(MyClassToEncode)
    expected = {
        "__class_name__": "MyClassToEncode",
    }
    assert result == expected

def test_json_encode_alias_client_module_proxy(json_encoder):
    """Test the AliasClientJSONEncoder default method to encode an AliasClientModuleProxyWrapper object."""

    module_data = {
        "__module_name__": "alias_api",
        "__members__": [],
    }
    module_proxy = proxy_wrapper.AliasClientModuleProxyWrapper(module_data)

    result = json_encoder.default(module_proxy)
    assert result == module_data

def test_json_encode_alias_client_property_proxy(json_encoder):
    """Test the AliasClientJSONEncoder default method to encode an AliasClientPropertyProxy object."""

    data = {
        "__property_name__": "test_prop",
    }
    proxy = proxy_wrapper.AliasClientPropertyProxyWrapper(data)

    result = json_encoder.default(proxy)
    assert result == data

def test_json_encode_alias_client_function_proxy(json_encoder):
    """Test the AliasClientJSONEncoder default method to encode an AliasClientFunctionProxy object."""

    data = {
        "__function_name__": "test_func",
        "__is_method__": False,
    }
    proxy = proxy_wrapper.AliasClientFunctionProxyWrapper(data)

    result = json_encoder.default(proxy)
    assert result == data

def test_json_encode_alias_client_class_proxy(json_encoder):
    """Test the AliasClientJSONEncoder default method to encode an AliasClientClassProxyWrapper object."""

    data = {
        "__class_name__": "my_class",
        "__members__": [],
    }
    proxy = proxy_wrapper.AliasClientClassProxyWrapper(data)

    result = json_encoder.default(proxy)
    assert result == data

def test_json_encode_alias_client_enum_proxy(json_encoder):
    """Test the AliasClientJSONEncoder default method to encode an AliasClientEnumProxyWrapper object."""

    data = {
        "__class_name__": "my_enum_class",
        "__enum_name__": "my_enum",
        "__enum_value__": 1,
    }
    proxy = proxy_wrapper.AliasClientEnumProxyWrapper(data)

    result = json_encoder.default(proxy)
    assert result == data

def test_json_encode_alias_client_object_proxy(json_encoder):
    """Test the AliasClientJSONEncoder default method to encode an AliasClientObjectProxy object."""

    data = {
        "__instance_id__": 1,
    }
    proxy = proxy_wrapper.AliasClientObjectProxy(data)

    result = json_encoder.default(proxy)
    assert result == data


####################################################################################################
# tk_framework_alias client_json AliasClientJSONDecoder
####################################################################################################

def test_json_decode_set(json_decoder):
    """Test the AliasClientJSONDecoder object_hook method to decode an api request."""

    set_value = [1, 2, 3]
    value = {
        "__type__": set,
        "__value__": [1, 2, 3],
    }
    result = json_decoder.object_hook(value)
    assert result == set(set_value)

def test_json_decode_exception(json_decoder):
    """Test the AliasClientJSONDecoder object_hook method to decode an exception object."""

    class MyException(Exception):
        pass
    msg = "A test exception"

    value = {
        "__exception_class_name__": MyException.__name__,
        "__msg__": msg,
        "__traceback__": None,
    }
    result = json_decoder.object_hook(value)

    assert isinstance(result, Exception)
    assert result.__class__.__name__ == MyException.__name__
    assert str(result) == msg

def test_json_decode_alias_module(json_decoder):
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    data = {
        "__module_name__": "alias_api",
        "__members__": [],
    }
    result = json_decoder.object_hook(data)

    assert isinstance(result, proxy_wrapper.AliasClientModuleProxyWrapper)
    assert result.module == result
    assert result.data == data

def test_json_decode_alias_property(json_decoder):
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    data = {
        "__property_name__": None,
    }
    result = json_decoder.object_hook(data)

    assert isinstance(result, proxy_wrapper.AliasClientPropertyProxyWrapper)
    assert result.data == data

def test_json_decode_alias_class(json_decoder):
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    data = {
        "__module_name__": "alias_api",
        "__class_name__": "my_class",
        "__members__": [],
    }
    result = json_decoder.object_hook(data)

    assert isinstance(result, proxy_wrapper.AliasClientClassProxyWrapper)
    assert result.data == data

def test_json_decode_alias_function(json_decoder):
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    data = {
        "__function_name__": "my_func",
        "__is_method__": False,
    }
    result = json_decoder.object_hook(data)

    assert isinstance(result, proxy_wrapper.AliasClientFunctionProxyWrapper)
    assert result.data == data

def test_json_decode_alias_enum(json_decoder):
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    data = {
        "__class_name__": "some_enum_class",
        "__enum_name__": "some_enum",
        "__enum_value__": 2,
    }
    result = json_decoder.object_hook(data)

    assert isinstance(result, proxy_wrapper.AliasClientEnumProxyWrapper)
    assert result.data == data

def test_json_decode_alias_object(json_decoder):
    """Test the AliasClientJSONDecoder object_hook method to decode api module object."""

    import alias_api_om
    proxy_wrapper.AliasClientObjectProxyWrapper.store_module("alias_api", alias_api_om)

    data = {
        "__module_name__": "alias_api",
        "__class_name__": "AlObjectType",
        "__instance_id__": 28,
    }
    result = json_decoder.object_hook(data)

    assert isinstance(result, proxy_wrapper.AliasClientObjectProxy)
    assert result.__class__.__name__ == "AlObjectType"
    assert result.data == data
    assert result.unique_id == 28
