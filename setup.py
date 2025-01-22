#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup script for the python-broadlink package.

This script defines the installation requirements and metadata for the package.
To install the package, run:
    python setup.py install
"""

from setuptools import setup, find_packages


VERSION = '0.20.0'

setup(
    name="broadlink",
    version=VERSION,
    author="Matthew Garrett",
    author_email="mjg59@srcf.ucam.org",
    url="http://github.com/mjg59/python-broadlink",
    packages=find_packages(),
    scripts=["cli/broadlink_cli"],
    install_requires=["cryptography>=3.2"],
    description="Python API for controlling Broadlink devices",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "broadlink-cli=broadlink.cli.broadlink_cli:main",
        ],
    },
)
