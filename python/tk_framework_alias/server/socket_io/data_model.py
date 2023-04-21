# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

import threading

from ..api import alias_api

# NOTE do we need to worry about cleaning up the registry in case it gets huge?


class AliasDataModel:
    """An object representation of the Alias universe."""

    def __init__(self):
        """Initialize"""

        self.__lock = threading.Lock()
        self.__registry = {}
        self.__events_registry = {}

    def destroy(self):
        """Destroy the scope."""

        self.__lock.acquire()
        try:
            # Clear the instance registry
            self.__registry.clear()

            # Remove all callbacks and clear the events registry
            for event in self.__events_registry:
                alias_api.remove_message_handlers(event)
            self.__events_registry.clear()

        finally:
            self.__lock.release()

    def get_instance(self, instance_id):
        """Return the instance object for the given id from the registry."""

        self.__lock.acquire()
        try:
            return self.__registry.get(instance_id)
        finally:
            self.__lock.release()

    def register_instance(self, instance_id, instance):
        """Store the instance in the registry."""

        self.__lock.acquire()
        try:
            self.__registry[instance_id] = instance
        finally:
            self.__lock.release()

    def unregister_instance(self, instance_id):
        """Remove the instance from the registry."""

        self.__lock.acquire()
        try:
            del self.__registry[instance_id]
        finally:
            self.__lock.release()

    def get_event_callbacks(self, event_id):
        """Return the instance object for the given id from the registry."""

        self.__lock.acquire()
        try:
            return self.__events_registry.get(event_id)
        finally:
            self.__lock.release()

    def register_event(self, event_id, event_callback_id):
        """Store the Alias event callback in the events registry."""

        self.__lock.acquire()
        try:
            self.__events_registry.setdefault(event_id, []).append(event_callback_id)
        finally:
            self.__lock.release()

    def unregister_event(self, event_id, event_callback_id=None):
        """Remove the Alias event callback from the events registry."""

        self.__lock.acquire()
        try:
            if event_id not in self.__events_registry:
                # The event does not have any callbacks registered.
                return

            if event_callback_id is None:
                # Remove all callbacks for the event
                del self.__events_registry[event_id]
            else:
                # Remove the specific event callback
                self.__events_registry[event_id].remove(event_callback_id)

        except ValueError:
            # Attempted to remove an event callback that does not exist.
            # should we log a warning?
            pass

        finally:
            self.__lock.release()
