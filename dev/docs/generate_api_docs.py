#!/usr/bin/env python
"""
Generate API documentation stub files for alias_api module.

This script generates .rst files by inspecting the compiled .pyd module at runtime,
which is necessary because autosummary doesn't work well with compiled extensions.
"""

import os
import sys
import inspect
from pathlib import Path

api_path = os.path.normpath(os.path.abspath(os.getenv("ALIAS_API_PATH")))
sys.path.insert(0, api_path)

# Add DLL directories
if hasattr(os, "add_dll_directory"):
    alias_install = os.getenv("ALIAS_INSTALL_PATH")
    if not os.path.exists(alias_install):
        raise ValueError(f"ALIAS_INSTALL_PATH does not exist")
    os.add_dll_directory(alias_install)
    os.add_dll_directory(api_path)

try:
    import alias_api_om as alias_api
except ImportError as e:
    print(f"ERROR: Could not import alias_api: {e}")
    sys.exit(1)

print("Successfully imported alias_api")

# Output directory
output_dir = Path(__file__).parent / "_autosummary"
output_dir.mkdir(exist_ok=True)


def get_members(module, include_private=False):
    """Get all public members of a module."""
    members = []
    for name in dir(module):
        if not include_private and name.startswith("_"):
            continue
        obj = getattr(module, name)
        members.append((name, obj))
    return members


def generate_module_rst(module, module_name):
    """Generate main module RST file."""
    members = get_members(module)

    classes = [(n, o) for n, o in members if inspect.isclass(o)]
    functions = [
        (n, o) for n, o in members if inspect.isfunction(o) or inspect.isbuiltin(o)
    ]

    rst_content = f"""{module_name}
{'=' * len(module_name)}

.. currentmodule:: {module_name}

.. automodule:: {module_name}

"""

    if classes:
        rst_content += "\nClasses\n-------\n\n.. autosummary::\n   :toctree:\n\n"
        for name, _ in classes:
            rst_content += f"   {module_name}.{name}\n"

    if functions:
        rst_content += "\nFunctions\n---------\n\n.. autosummary::\n   :toctree:\n\n"
        for name, _ in functions:
            rst_content += f"   {module_name}.{name}\n"

    # Write automodule directives for full documentation
    rst_content += "\n\nModule Contents\n---------------\n\n"

    if classes:
        rst_content += "\nClasses\n~~~~~~~\n\n"
        for name, _ in classes:
            rst_content += f"""
.. autoclass:: {module_name}.{name}
   :members:
   :undoc-members:
   :show-inheritance:

"""

    if functions:
        rst_content += "\nFunctions\n~~~~~~~~~\n\n"
        for name, _ in functions:
            rst_content += f"""
.. autofunction:: {module_name}.{name}

"""

    return rst_content


def generate_class_rst(module_name, class_name, cls):
    """Generate RST file for a class."""
    rst_content = f"""{module_name}.{class_name}
{'=' * (len(module_name) + len(class_name) + 1)}

.. currentmodule:: {module_name}

.. autoclass:: {class_name}
   :members:
   :undoc-members:
   :show-inheritance:
"""
    return rst_content


def generate_function_rst(module_name, func_name, func):
    """Generate RST file for a function."""
    rst_content = f"""{module_name}.{func_name}
{'=' * (len(module_name) + len(func_name) + 1)}

.. currentmodule:: {module_name}

.. autofunction:: {func_name}
"""
    return rst_content


def main():
    module_name = "alias_api"
    module = alias_api

    # Generate main module file
    print(f"Generating {module_name}.rst...")
    rst_content = generate_module_rst(module, module_name)
    output_file = output_dir / f"{module_name}.rst"
    output_file.write_text(rst_content, encoding="utf-8")
    print(f"  Created: {output_file}")

    # Generate individual class and function files
    members = get_members(module)

    for name, obj in members:
        if inspect.isclass(obj):
            print(f"Generating {module_name}.{name}.rst...")
            rst_content = generate_class_rst(module_name, name, obj)
            output_file = output_dir / f"{module_name}.{name}.rst"
            output_file.write_text(rst_content, encoding="utf-8")
            print(f"  Created: {output_file}")

        elif inspect.isfunction(obj) or inspect.isbuiltin(obj):
            print(f"Generating {module_name}.{name}.rst...")
            rst_content = generate_function_rst(module_name, name, obj)
            output_file = output_dir / f"{module_name}.{name}.rst"
            output_file.write_text(rst_content, encoding="utf-8")
            print(f"  Created: {output_file}")

    print(
        f"\nGeneration complete! Created {len(list(output_dir.glob('*.rst')))} files in {output_dir}"
    )


if __name__ == "__main__":
    main()
