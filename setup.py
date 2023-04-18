# -*- coding: utf-8 -*-
from setuptools import setup
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version('gluster_georep_tools')
except PackageNotFoundError:
    __version__ = "unknown"

setup(
    name="gluster-georep-tools",
    version=__version__,
    packages=["gluster_georep_tools",
              "gluster_georep_tools.status",
              "gluster_georep_tools.setup"],
    include_package_data=True,
    install_requires=['paramiko', 'glustercli', 'prettytable'],
    entry_points={
        "console_scripts": [
            "gluster-georep-setup = gluster_georep_tools.setup.cli:main",
            "gluster-georep-status = gluster_georep_tools.status.cli:main",
        ]
    },
    platforms="linux",
    zip_safe=False,
    author="Aravinda Vishwanathapura",
    author_email="mail@aravindavk.in",
    description="Gluster Geo-replication tools",
    license="MIT",
    keywords="gluster, tool, geo-replication",
    url="https://github.com/aravindavk/gluster-georep-tools",
    long_description="""
    Gluster Geo-replication Tools
    """,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python"
    ],
)
