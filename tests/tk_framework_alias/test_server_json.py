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
import inspect

from tk_framework_alias.server.socket_io import server_json
from tk_framework_alias.server.api import alias_api
from tk_framework_alias.server import alias_bridge



####################################################################################################
# fixtures
####################################################################################################

@pytest.fixture(autouse=True)
def json_encoder():
    """Fixture to return an instance of the AliasServerJSONEncoder class."""

    return server_json.AliasServerJSONEncoder()

@pytest.fixture(autouse=True)
def json_decoder():
    """Fixture to return an instance of the AliasJSONDecoder class."""

    return server_json.AliasServerJSONDecoder()

####################################################################################################
# tk_framework_alias server json
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
    """Test the AliasServerJSONEncoder default method to encode set objects."""

    result = json_encoder.default(value)
    expected = {
        "__type__": set,
        "__value__": list(value)
    }
    assert result == expected

def test_json_encode_property(json_encoder):
    """Test the AliasServerJSONEncoder default method to encode property objects."""

    class MyClass:
        @property
        def my_class_property(self):
            pass

    result = json_encoder.default(MyClass.my_class_property)
    expected = {
        "__property_name__": None,
    }
    assert result == expected

def test_json_encode_exception(json_encoder):
    """Test the AliasServerJSONEncoder default method to encode Exception objects."""

    msg = "test exception"
    my_exception = Exception(msg)

    result = json_encoder.default(my_exception)
    expected = {
        "__exception_class_name__": "Exception",
        "__msg__": msg,
        "__traceback__": None,
    }
    assert result == expected

def test_json_encode_method(json_encoder):
    """Test the AliasServerJSONEncoder default method to encode method objects."""

    class MyClass:
        def my_class_method(self):
            pass
    my_class_obj = MyClass()

    result = json_encoder.default(my_class_obj.my_class_method)
    expected = {
        "__function_name__": my_class_obj.my_class_method.__name__,
        "__is_method__": True,
    }
    assert result == expected

def test_json_encode_function(json_encoder):
    """Test the AliasServerJSONEncoder default method to encode function objects."""

    def my_func():
        pass

    result = json_encoder.default(my_func)
    expected = {
        "__function_name__": my_func.__name__,
        "__is_method__": False,
    }
    assert result == expected


@pytest.mark.parametrize(
    "class_type",
    [
        (alias_api.AlDagNode),
        (alias_api.AlLayer),
        (alias_api.AlCoordinateSystem),
    ]
)
def test_json_encode_class_type(json_encoder, class_type):
    """Test the AliasServerJSONEncoder default method to encode class objects."""

    members = inspect.getmembers(class_type)
    class_members = []
    for member_name, member_value in members:
        if inspect.isclass(member_value):
            class_name = member_value.__name__
            value = {
                "__module_name__": member_value.__module__,
                "__class_name__": class_name,
                "__members__": None,
            }
        else:
            value = member_value
        class_members.append((member_name, value))

    result = json_encoder.default(class_type)
    expected = {
        "__module_name__": class_type.__module__,
        "__class_name__": class_type.__name__,
        "__members__": class_members,
    }
    assert result == expected

@pytest.mark.parametrize(
    "enum",
    [
        (alias_api.AlMessageType.StageActive),
        (alias_api.AlStatusCode.Success),
        (alias_api.AlStatusCode.Failure),
        (alias_api.AlObjectType.DagNodeType),
        (alias_api.AlDisplayModeType.BoundingBox),
    ]
)
def test_json_encode_alias_api_enum(json_encoder, enum):
    """Test the AliasServerJSONEncoder default method to encode Alias API enum objects."""

    result = json_encoder.default(enum)
    expected = {
        "__class_name__": enum.__class__.__name__,
        "__enum_name__": enum.name,
        "__enum_value__": enum.value,
    }
    assert result == expected

@pytest.mark.parametrize(
    "alias_object",
    [
        (alias_api.create_layer("MyLayer")),
        (alias_api.create_layer_folder("MyFolder")),
        (alias_api.create_shader()),
        (alias_api.create_layered_shader()),
        (alias_api.create_switch_shader()),
        (alias_api.create_orthographic_camera(alias_api.AlWindow.AlViewType.Top)),
        (alias_api.create_perspective_camera()),
    ]
)
def test_json_encode_alias_api_object(json_encoder, alias_object):
    """Test the AliasServerJSONEncoder default method to encode Alias API objects."""

    instance_id = id(alias_object)

    result = json_encoder.default(alias_object)
    expected = {
        "__module_name__": alias_object.__module__,
        "__class_name__": alias_object.__class__.__name__,
        "__instance_id__": instance_id,
    }
    assert result == expected

    # Check that the object was added to the data model
    data_model = alias_bridge.AliasBridge().alias_data_model
    instance = data_model.get_instance(instance_id)
    assert instance is alias_object

# def test_json_encode_descriptor(json_encoder, value):
#     """Test the AliasServerJSONEncoder default method to encode descriptor objects."""

# def test_json_encode_mapping_proxy_type(json_encoder, value):
#     """Test the AliasServerJSONEncoder default method to encode MappingProxyType objects."""

# def test_json_encode_module_spec(json_encoder, value):
#     """Test the AliasServerJSONEncoder default method to encode ModuleSpec objects."""

# def test_json_encode_extension_file_loader(json_encoder, value):
#     """Test the AliasServerJSONEncoder default method to encode ExtensionFileLoader objects."""

# def test_json_encode_getsetdescriptor(json_encoder, value):
#     """Test the AliasServerJSONEncoder default method to encode getsetdescriptor objects."""

# def test_json_encode_memberdescriptor(json_encoder, value):
#     """Test the AliasServerJSONEncoder default method to encode memberdescriptor objects."""

# def test_json_encode_callable(json_encoder, value):
#     """Test the AliasServerJSONEncoder default method to encode callable objects."""
