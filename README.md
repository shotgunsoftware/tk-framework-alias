[![Python 3.7 3.9](https://img.shields.io/badge/python-3.7%20%7C%203.9-blue.svg)](https://www.python.org/)
[![Build Status](https://dev.azure.com/shotgun-ecosystem/Toolkit/_apis/build/status/Frameworks/tk-framework-alias?branchName=main)](https://dev.azure.com/shotgun-ecosystem/Toolkit/_build/latest?definitionId=62&branchName=main)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# tk-framework-alias

Toolkit framework for integration with Autodesk Alias.

### Support

- Windows only

## Development

### How to set up your development environment

- Please set all necessary variables in `dev\env.cmd`

This is what the env file should look like:
```
TARGET_VERSION=1.1.3 # Make sure this matches the tk-framework-alias version you will be releasing

TKCORE_VERSION=0.19.19  # This core version is expected to exist in your bundle cache

PYTHON_EXE=/path/to/python.exe
```

Follow [this link](https://developer.shotgridsoftware.com/7c9867c0/#bundle-cache)
  to find out where your bundle cache is located.

### To build the Alias plugin and install it:

```
cd path/to/tk-framework-alias
cd dev
make build
make install
```

### To remove the latest built plugin bundle

```
cd path/to/tk-framework-alias
cd dev
make clean
```

### Notes on editing the env file (`env.cmd`)

Changes to the env file (`env.cmd`) will typically not be tracked in git. The information contained in these files is specific to a particular development environment, so tracking changes to that data in git is undesirable.

If you need to make changes to these files, you can use the following commands:

```
git update-index --no-skip-worktree dev/env.mk dev/env.cmd
git add dev\env.*
git commit -m "your message"
git update-index --skip-worktree dev/env.mk dev/env.cmd
```
