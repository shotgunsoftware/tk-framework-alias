# Copyright (c) 2026 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

"""Helpers for the on-disk Alias API module cache."""

import json

from ...extension_api_classes import ALIAS_API_EXTENSIONS_CLASS_NAME


def alias_api_cache_needs_extension_rebuild(cache_filepath):
    """
    Return True when a reused cache encodes ``AliasApiExtensions`` without methods.

    Pre-fix caches used circular-ref stubs (``__members__``: null) and the client
    installer cannot discover extension RPC names from them.
    """

    try:
        with open(cache_filepath, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except (OSError, json.JSONDecodeError, TypeError):
        return True

    if not isinstance(payload, dict):
        return False

    for name, value in payload.get("__members__") or []:
        if name != ALIAS_API_EXTENSIONS_CLASS_NAME:
            continue
        if not isinstance(value, dict):
            return True
        return value.get("__members__") is None

    return False
