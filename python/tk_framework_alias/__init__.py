# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

# Add our third-party packages to sys.path. Non-C Extension packages are zipped up to save on
# space, but C Extension pacakges cannot be distributed via ZipFile so they have been installed
# locally in the framework dist directory
import os
import sys

major = sys.version_info.major
minor = sys.version_info.minor
python_dir = f"python{major}.{minor}"

dist_path = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),  # ./python/tk_framework_alias
        os.pardir,  # ./python
        os.pardir,  # .
        "dist",
        python_dir,
    )
)
sys.path.insert(0, dist_path)
sys.path.insert(0, os.path.join(dist_path, "pkgs.zip"))
sys.path.insert(0, os.path.join(dist_path, "lib"))

# NOTE For python >= 3.9 do we need to use os.add_dll_directory?

from . import client
from . import server
