# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.


# AliasBridge exceptions
# ----------------------------------------------------------------------------------------

class AliasBridgeException(Exception):
    """Exception for AliasBridge errors."""

class ClientAlreadyRegistered(AliasBridgeException):
    """Exception for AliasBridge when attempting to register a client that is already registered."""

class ClientNameReservered(AliasBridgeException):
    """Exception for AliasBridge when attempting to register a client whose name is in the reserved list."""

class ServerAlreadyRunning(AliasBridgeException):
    """Exception for AliasBridge when attempting to connect to server when it is already running."""

class QtImportError(AliasBridgeException):
    """Exception for AliasBridge when attempting to import Qt."""


# AliasServerNamespace exceptions
# ----------------------------------------------------------------------------------------

class ClientAlreadyConnected(Exception):
    """Exception for AliasServerNamespace errors."""


# AliasServerJSON exceptions
# ----------------------------------------------------------------------------------------

class AliasServerJSONDecoderError(Exception):
    """Exception for Alias server JSON decoder errors."""


# AliasPythonApi exceptions
# ----------------------------------------------------------------------------------------

class AliasPythonApiImportError(Exception):
    """Exception for Alias Python API import errors."""


# AliasApiRequest exceptions
# ----------------------------------------------------------------------------------------

class AliasApiRequestException(Exception):
    """Exception for Alias API request errors."""

class AliasApiRequestNotValid(AliasApiRequestException):
    """Exception for Alias API request not valid error."""

class AliasApiRequestNotSupported(AliasApiRequestException):
    """Exception for Alias API request not supported error."""

class AliasApiPostProcessRequestError(AliasApiRequestException):
    """Exception for Alias API request post process error."""
