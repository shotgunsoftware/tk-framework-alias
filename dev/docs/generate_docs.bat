@echo off
REM Generate API documentation stub files for alias_api

setlocal

@REM Environment variables to set before running this script:
@REM set ALIAS_API_VERSION=8.0.0-Alias2027.0
@REM set ALIAS_VERSION=2027.0
@REM set PYTHON_VERSION=3.11
@REM set SPHINX_INSTALL_DIR=..\..\docs\_static\alias_api\%ALIAS_VERSION%
@REM set ALIAS_INSTALL_PATH=C:\Program Files\Autodesk\AliasAutoStudio%ALIAS_VERSION%\bin
@REM set ALIAS_API_PATH=..\..\dist\Alias\python%PYTHON_VERSION%\%ALIAS_VERSION%

echo ALIAS_API_VERSION: %ALIAS_API_VERSION%
echo ALIAS_VERSION: %ALIAS_VERSION%
echo PYTHON_VERSION: %PYTHON_VERSION%
echo SPHINX_INSTALL_DIR: %SPHINX_INSTALL_DIR%
echo ALIAS_INSTALL_PATH: %ALIAS_INSTALL_PATH%
echo ALIAS_API_PATH: %ALIAS_API_PATH%

echo Generating API documentation from alias_api.pyd...
echo Checking python version...
python --version
python generate_api_docs.py

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Documentation generation failed
    exit /b 1
)

echo.
echo Success! API documentation stub files have been generated.

echo Building Alias Python API documentation...
sphinx-build -b html . %SPHINX_INSTALL_DIR%

echo Building tk-framework-alias documentation...
PUSHD ..\..\docs
tk-docs-preview
POPD

endlocal
