import pytest
import os
import sys
import datetime
import os

# # Determine the Alias Python API module to import based on the sys exe
# if os.path.basename(sys.executable) == "Alias.exe":
#     # OpenAlias
#     import alias_api
# else:
#     # OpenModel

#     # For OpenModel, we need to ensure that the Alias DLLs are in the search path.
#     # OpenAlias does not have to worry about this because all the DLLs are in the
#     # exe path, which is automatically added to the search path.
#     if hasattr(os, "add_dll_directory"):
#         # For Python versions >= 3.8
#         alias_dll_path = os.environ.get("APA_ALIAS_DLL_DIR")
#         if not alias_dll_path:
#             raise Warning(
#                 (
#                     "Alias DLL directory path not set.\n"
#                     "This will cause the Alias Python API fail to import because it cannot "
#                     "find the Alias DLLs to load.\n"
#                     "Set the APA_ALIAS_DLL_DIR=<path_to_alias_install_bin_dir> environment "
#                     "variable to add this path to the DLL search path."
#                 )
#             )
#         with os.add_dll_directory(alias_dll_path):
#             import alias_api_om as alias_api
#     else:
#         # For Python version < 3.8, the PATH environment variable must have the Alias DLL path
#         # add to it before running pytest
#         import alias_api_om as alias_api


############################################################################### 
# pytest configuration
############################################################################### 

def pytest_configure(config):
    """
    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.
    """

    print("Configuring...")

    import debugpy
    debugpy.listen(5678)
    debugpy.wait_for_client()
    # debugpy.breakpoint()

    # Add the python modules to the sys.path for import
    base_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "python")
    )
    tk_framework_alias = os.path.abspath(os.path.join(base_dir, "tk_framework_alias"))
    tk_framework_alias_utils = os.path.abspath(os.path.join(base_dir, "tk_framework_alias_utils"))
    sys.path.extend([
        base_dir,
        tk_framework_alias,
        tk_framework_alias_utils,
    ])

    # TODO run tests for all supported api?
    # Set up the environment
    os.environ["ALIAS_PLUGIN_CLIENT_ALIAS_VERSION"] = "2024.0"

def pytest_sessionstart(session):
    """
    Called after the Session object has been created and
    before performing collection and entering the run test loop.
    """

    print("Timestamp:  {}".format(datetime.datetime.now()))

    from tk_framework_alias.server.api import alias_api

    print("Alias API Python {mode}".format(mode="OpenModel" if alias_api.__open_model__ else "OpenAlias"))
    print("\tv{}".format(alias_api.__version__))
    print("\tAlias v{}".format(alias_api.__alias_version__))
    print("\tPython v{}".format(sys.version))
    print("\tPython exe: {}".format(sys.executable))
    print("\t{}".format(alias_api.__file__))

    # Ensure Alias Universe is already initialized and ready.
    alias_api.initialize_universe()


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before
    returning the exit status to the system.
    """


def pytest_unconfigure(config):
    """
    called before test process is exited.
    """


############################################################################### 
# Import Global Fixtures
############################################################################### 

from fixtures.globals import *


############################################################################### 
# OpenAlias Global Fixtures
############################################################################### 

# @pytest.fixture(scope="session")
# def alpy(request):
#     return alias_api
