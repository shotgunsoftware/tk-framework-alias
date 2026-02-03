# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

api_path = os.path.normpath(os.path.abspath(os.getenv("ALIAS_API_PATH")))
print(f"ALIAS_API_PATH: {api_path}")
sys.path.insert(0, api_path)

if hasattr(os, "add_dll_directory"):
    # Add the Alias installation directory
    alias_install_path = os.getenv("ALIAS_INSTALL_PATH")
    print(f"ALIAS_INSTALL_PATH: {alias_install_path}")
    if not os.path.exists(alias_install_path):
        raise ValueError(f"ALIAS_INSTALL_PATH does not exist")
    os.add_dll_directory(alias_install_path)
    os.add_dll_directory(api_path)

# Try to import alias_api to verify DLL loading
try:
    import alias_api

    print("Successfully imported alias_api")
except (ImportError, OSError) as e:
    print(f"ERROR: Could not import alias_api: {e}")
    print("Please check that:")
    print("  1. ALIAS_INSTALL_PATH environment variable is set correctly")
    print("  2. ALIAS_API_PATH environment variable is set correctly")
    print(f"  3. Path is correct: {api_path}")
    print(
        f"  4. The Python version used to build the docs is the same as the Python version the alias_api.pyd was built with"
    )
    raise


# -- Project information -----------------------------------------------------

project = "Alias Python API"
version = os.getenv("ALIAS_API_VERSION", "0.0.0")
copyright = os.getenv("APA_COPYRIGHT", "2026, Autodesk, Inc")
author = "Autodesk, Inc"
print(f"Version: {version}")
print(f"Copyright: {copyright}")

# -- General configuration ---------------------------------------------------

master_doc = "index"

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    # "breathe",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Autosummary configuration
# For .pyd files (compiled C++ extensions), autosummary's automatic generation
# doesn't work well because it tries to locate source files.
# Instead, use the generate_api_docs.py script to create stub files:
#   1. Build the project: call scripts\build.bat
#   2. Generate API docs: cd docs && python generate_api_docs.py
#   3. Build documentation: sphinx-build -b html . ..\build\docs
#
# The generated .rst files use autodoc directives which work with .pyd files
# through runtime introspection (using Python's inspect module).
autosummary_generate = False
autosummary_imported_members = True

# Configure autodoc - this is what actually extracts documentation from .pyd files
# autodoc uses Python's introspection (inspect module) to read docstrings,
# function signatures, and class information at runtime
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "private-members": False,  # Don't document private members (starting with _)
    "special-members": False,  # Don't document special members like __init__
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_rtd_theme"

# Theme options for sphinx_rtd_theme 1.0.0
html_theme_options = {
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 4,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

# Define |version| substitution
rst_prolog = """
.. |version| replace:: {version}
""".format(version=version)
