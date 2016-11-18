# -*- coding: utf-8 -*-
"""
    gluster-georep-tools.setup.py
    :copyright: (c) 2016 by Aravinda VK
    :license: MIT, see LICENSE for more details.
"""

from setuptools import setup


setup(
    name="gluster-georep-tools",
    version="0.2",
    packages=["gluster_georep_tools",
              "gluster_georep_tools.status",
              "gluster_georep_tools.setup"],
    include_package_data=True,
    install_requires=['argparse', 'paramiko', 'glustercli'],
    entry_points={
        "console_scripts": [
            "gluster-georep-setup = gluster_georep_tools.setup.cli:main",
            "gluster-georep-status = gluster_georep_tools.status.cli:main",
        ]
    },
    platforms="linux",
    zip_safe=False,
    author="Aravinda VK",
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
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 2 :: Only"
    ],
)
