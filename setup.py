from setuptools import setup, find_packages

setup(
    name="alias-python-api",
    version="0.0.1",
    packages=find_packages(where="python"),
    package_dir={"": "python"},

    platforms=["win32", "win-amd64"],

    # Metadata
    author="Stacey Oue",
    author_email="stacey.oue@autodesk.com",
    description="Alias Python API communication framework.",

    long_description=open('README.md').read(),
    # long_description = file: README.md
    long_description_content_type = "text/markdown",

    url="https://github.com/shotgunsoftware/tk-framework-alias",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Python Software Foundation License',
        # 'Programming Language :: Python :: 3.7',
        # 'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],

    # python_requires = >=3.7,

    # Dependencies
    install_requires=[
        "cryptography",
        "eventlet",
        # "PySide2==5.15.0",
        "PySide6==6.2.1",
        "python-socketio",
        "requests",
        "websocket-client",
    ],

    data_files=[
        ('alias_api', ['python/api/alias_api.pyd']),
        ('Lib/site-packages/tk_framework_alias/client/gui/console', ['python/tk_framework_alias/client/gui/console/style.qss']),
    ]
)
