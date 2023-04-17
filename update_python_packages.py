# Copyright (c) 2023 Autodesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

import sys
sys.path.append("C:\\python_libs")
import ptvsd
ptvsd.enable_attach(address=("localhost", 5679))
ptvsd.wait_for_attach()

import subprocess
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from distutils.dir_util import copy_tree


def zip_recursively(zip_file, root_dir, folder_name):
    for root, _, files in os.walk(root_dir / folder_name):
        for file in files:
            full_file_path = Path(os.path.join(root, file))
            zip_file.write(full_file_path, full_file_path.relative_to(root_dir))


with TemporaryDirectory() as temp_dir:

    # Pip install everything and capture everything that was installed.
    subprocess.run(
        [
            "python",
            "-m",
            "pip",
            "install",
            "-r",
            "requirements.txt",
            "--no-compile",
            # The combination of --target and --upgrade forces pip to install
            # all packages to the temporary directory, even if an already existing
            # version is installed
            "--target",
            temp_dir,
            "--upgrade",
        ]
    )
    subprocess.run(
        ["python", "-m", "pip", "freeze", "--path", temp_dir],
        stdout=open("frozen_requirements.txt", "w"),
    )

    # Quickly compute the number of requirements we have.
    nb_dependencies = len([_ for _ in open("frozen_requirements.txt", "rt")])

    # Figure out if those packages were installed as single file packages or folders.
    # package_names = [
    #     package_name
    #     for package_name in os.listdir(temp_dir)
    #     if "info" not in package_name and package_name not in ("bin", "include")
    # ]
    package_names = []

    # Handle C extension modules (dynamic libraries .pyd, .dll, .so)
    c_extension_packages = []

    with os.scandir(temp_dir) as entries:
        for entry in entries:
            if "info" in entry.name or entry.name in ("bin", "include"):
                continue

            if entry.is_dir():
                package_dir = os.path.join(temp_dir, entry.name)
                with os.scandir(package_dir) as package_entries:
                    for package_entry in package_entries:
                        if not package_entry.is_file():
                            continue
                        ext = Path(package_entry.path).suffix
                        if ext.lower() in (".pyd", "so", "dll"):
                            c_extension_packages.append(entry.name)
                            break
                    else:
                        package_names.append(entry.name)
            else:
                package_names.append(entry.name)
        
    # Make sure we found as many Python packages as there are packages listed inside frozen_requirements.txt
    assert len(package_names) + len(c_extension_packages) == nb_dependencies

    # Create the distribution directory
    dist_dir = os.path.join(
        os.path.dirname(__file__),
        "dist",
    )
    if not os.path.exists(dist_dir):
        os.mkdir(dist_dir)
    
    # Copy the include directory to the dist dir
    include_dir = os.path.join(temp_dir, "include", "python")
    if os.path.exists(include_dir):
        copy_tree(include_dir, os.path.join(dist_dir, "include"))

    pkgs_zip = ZipFile(Path(dist_dir) / "pkgs.zip", "w")

    for package_name in package_names:
        print(f"Zipping {package_name}...")

        # If we have a .py file to zip, simple write it
        temp_dir_path = Path(temp_dir)
        full_package_path = temp_dir_path / package_name

        if full_package_path.suffix == ".py":
            pkgs_zip.write(full_package_path, full_package_path.relative_to(temp_dir))

        else:
            # Otherwise zip package folders recursively.
            zip_recursively(pkgs_zip, temp_dir_path, package_name)

    if c_extension_packages:
        print(f"Copying C Extension package {package_name}...")

        # Create the library directory to copy dynamic lib packages
        lib_dir = os.path.join(dist_dir, "lib")
        if not os.path.exists(lib_dir):
            os.mkdir(lib_dir)

        for package_name in c_extension_packages: 
            package_path = os.path.join(temp_dir, package_name)
            dist_package_path = os.path.join(lib_dir, package_name)
            copy_tree(package_path, dist_package_path)
