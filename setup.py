#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import warnings

from setuptools import setup, find_packages

try:
    import cryptography
    dynamic_requires = ['cryptography>=2.1.1']
except ImportError:
    dynamic_requires = ["pyaes==1.6.0"]

# For Hysen thermostatic heating controller
dynamic_requires.append('PyCRC')

version = '0.11.1'

setup(
    name='broadlink',
    version=version,
    author='Matthew Garrett',
    author_email='mjg59@srcf.ucam.org',
    url='http://github.com/mjg59/python-broadlink',
    packages=find_packages(),
    scripts=[],
    install_requires=dynamic_requires,
    description='Python API for controlling Broadlink IR controllers',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    include_package_data=True,
    zip_safe=False,
)
