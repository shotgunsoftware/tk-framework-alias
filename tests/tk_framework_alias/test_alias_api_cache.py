# Copyright (c) 2026 Autodesk, Inc.

"""Tests for Alias API on-disk cache validation."""

import json
import tempfile

from tk_framework_alias.server.socketio import alias_api_cache


def test_detects_empty_alias_api_extensions_stub():
    """Stale caches with ``__members__``: null should trigger rebuild."""

    payload = {
        "__module_name__": "alias_api",
        "__members__": [
            [
                "AliasApiExtensions",
                {
                    "__module_name__": "alias_api",
                    "__class_name__": "AliasApiExtensions",
                    "__members__": None,
                },
            ]
        ],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as fp:
        json.dump(payload, fp)
        path = fp.name

    assert alias_api_cache.alias_api_cache_needs_extension_rebuild(path) is True


def test_accepts_cache_with_extension_members():
    """Caches that embed extension RPC members are reusable."""

    payload = {
        "__module_name__": "alias_api",
        "__members__": [
            [
                "AliasApiExtensions",
                {
                    "__module_name__": "alias_api",
                    "__class_name__": "AliasApiExtensions",
                    "__members__": [
                        [
                            "has_picked_items",
                            {
                                "__function_name__": "has_picked_items",
                                "__is_method__": True,
                            },
                        ]
                    ],
                },
            ]
        ],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as fp:
        json.dump(payload, fp)
        path = fp.name

    assert alias_api_cache.alias_api_cache_needs_extension_rebuild(path) is False
