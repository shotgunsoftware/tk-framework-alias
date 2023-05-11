# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.

import importlib.util
import os
import sys
from ..utils.exceptions import AliasPythonApiImportError

# Python module names for specific Alias modes
OPEN_ALIAS_API_NAME = "alias_api"
OPEN_MODEL_API_NAME = "alias_api_om"

# The Alias Python API (APA) python module is decided based on the current version of Alias
# that is running. Defined here is the Alias version grouping:
#
#    < v2020.3              -- use APA from folder alias2019-alias2020.2
#   >= v2020.3 & < v2021.3  -- use APA from folder alias2020.3-alias2021
#   >= v2021.3 & < v2022.2  -- use APA from folder alias2021.3
#   >= v2022.2 & < v2023.0  -- use APA from folder alias2022.2
#   == v2023.0              -- use APA from folder alias2023.0
#   == v2023.1              -- use APA from folder alias2023.1
#
# NOTE this Alias version mapping to python api version is deprecated since 2023.0
# There should be an api folder for each Alias version. Remove these version mappings as older
# versions of Alias are dropped from support.
ALIAS_API = {
    "alias2022.2": {"min_version": "2022.2", "max_version": "2023.0"},
    "alias2021.3": {"min_version": "2021.3", "max_version": "2022.2"},
    "alias2020.3-alias2021": {"min_version": "2020.3", "max_version": "2021.3"},
    "alias2019-alias2020.2": {"min_version": "2019", "max_version": "2020.3"},
}


def version_cmp(version1, version2):
    """
    Compare the version strings.

    :param version1: A version string to compare against version2 e.g. 2022.2
    :param version2: A version string to compare against version1 e.g. 2021.3.1

    :return: The result of the comparison:
         1 - version1 is greater than version2
         0 - version1 and version2 are equal
        -1 - version1 is less than version2
    :rtype: int
    """

    # This will split both the versions by the '.' char to get the major, minor, patch values
    arr1 = version1.split(".")
    arr2 = version2.split(".")
    n = len(arr1)
    m = len(arr2)

    # Converts to integer from string
    arr1 = [int(i) for i in arr1]
    arr2 = [int(i) for i in arr2]

    # Compares which list is bigger and fills the smaller list with zero (for unequal
    # delimeters)
    if n > m:
        for i in range(m, n):
            arr2.append(0)
    elif m > n:
        for i in range(n, m):
            arr1.append(0)

    # Returns 1 if version1 is greater
    # Returns -1 if version2 is greater
    # Returns 0 if they are equal
    for i in range(len(arr1)):
        if arr1[i] > arr2[i]:
            return 1
        elif arr2[i] > arr1[i]:
            return -1
    return 0


def get_alias_version():
    """Return the Alias version."""

    # Get the Alias version from the environment variable
    version = os.environ.get("ALIAS_PLUGIN_CLIENT_ALIAS_VERSION")
    if not version:
        msg = "Alias version is not set. Set the environment variable ALIAS_PLUGIN_CLIENT_ALIAS_VERSION (e.g. 2022.2)."
        raise AliasPythonApiImportError(msg)

    return version


def get_module_path(module_name, alias_version):
    """Return the file path to the Alias Python API module to use."""

    python_version = "{major}.{minor}".format(
        major=sys.version_info.major,
        minor=sys.version_info.minor,
    )
    python_folder_name = "python{}".format(python_version)

    # Determine the name of the folder containing the files to import according to the version
    # of Alias

    # First try to get the api folder directly matching the running version of Alias
    api_folder_name = "alias{version}".format(version=alias_version)
    api_folder_path = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            python_folder_name,
            api_folder_name,
        )
    )

    if not os.path.exists(api_folder_path):
        # This is an older build, look up based on Alias version grouping.
        api_folder_path = None
        for api_folder_name in ALIAS_API:
            min_version = ALIAS_API[api_folder_name].get("min_version")
            if min_version and version_cmp(alias_version, min_version) < 0:
                continue

            max_version = ALIAS_API[api_folder_name].get("max_version")
            if max_version and version_cmp(alias_version, max_version) >= 0:
                continue

            # Found the api folder name, now try to get the full path.
            api_folder_path = os.path.normpath(
                os.path.join(
                    os.path.dirname(__file__),
                    python_folder_name,
                    api_folder_name,
                )
            )
            break

    if not api_folder_path or not os.path.exists(api_folder_path):
        raise AliasPythonApiImportError(
            "Failed to get Alias Python API module path for Alias {alias_version} and Python {py_version}".format(
                alias_version=alias_version, py_version=python_version
            )
        )

    module_path = os.path.normpath(
        os.path.join(
            api_folder_path,
            "{}.pyd".format(module_name),
        )
    )
    if not os.path.exists(module_path):
        # raise AliasPythonApiImportError("Module does not exist {}".format(module_path))
        return None

    return module_path


def get_alias_api_module():
    """
    Import the right Alias Python API module according to the criteria:
        - the version of Alias
        - the execution mode (interactive vs non-interactive)

    The Alias Python API supports Python >= 3
    """

    # Determine the module name based on if running in OpenAlias or OpenModel
    # If the executable is Alias, then it is OpenAlias, else OpenModel.
    is_open_model = os.path.basename(sys.executable) != "Alias.exe"
    module_name = OPEN_MODEL_API_NAME if is_open_model else OPEN_ALIAS_API_NAME
    alias_version = get_alias_version()

    module_path = get_module_path(module_name, alias_version)
    if not module_path:
        return None

    # Find and create the module spec object for the Alias Python API
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if not spec:
        raise AliasPythonApiImportError(
            "Could not find the Alias Python API module {}".format(module_path)
        )

    try:
        # module_from_spec will add the api module to the sys.modules
        api_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api_module)
    except Exception as e:
        info_msg = (
            "Running: Alias v{alias_version}, Python v{py_major}.{py_minor}.{py_micro}.\n\n"
            "Attempted to import Alias Python API {apa_name}.pyd from: {apa_path}\n\n"
            "Failed import may be caused by a mismatch between the running Alias or Python version and "
            "the versions used to compile the Alias Python API."
        ).format(
            apa_name=module_name,
            apa_path=module_path,
            alias_version=alias_version,
            py_major=sys.version_info.major,
            py_minor=sys.version_info.minor,
            py_micro=sys.version_info.micro,
        )
        raise AliasPythonApiImportError(
            "{error}\n\n{info}".format(error=str(e), info=info_msg)
        )

    return api_module


#
# Get the Alias API module and and make it available through this api module global variable
# 'alias_api', e.g. api.alias_api
#
if hasattr(os, "add_dll_directory"):
    # For Python >= 3.9, ensure that the DLL path is in the search path by using the os method
    # add_dll_directory. Starting in 3.9, the sys.path is no longer used to find DLLs.
    alias_bin_path = os.environ.get("ALIAS_PLUGIN_CLIENT_ALIAS_EXECPATH")
    if not alias_bin_path:
        raise AliasPythonApiImportError(
            "Couldn't get Alias bin path: set the environment variable ALIAS_PLUGIN_CLINET_ALIAS_EXECPATH."
        )
    alias_dll_path = os.path.dirname(alias_bin_path)
    with os.add_dll_directory(alias_dll_path):
        alias_api = get_alias_api_module()
else:
    alias_api = get_alias_api_module()
