#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from setuptools import setup, find_packages
import sys
import warnings

try:
    import pyaes
    dynamic_requires = ["pyaes==1.6.0"]
except ImportError as e:
    dynamic_requires = ['pycryptodome==3.6.6']

# For Hysen thermostatic heating controller
dynamic_requires.append('PyCRC')

version = 0.9

setup(
    name='broadlink',
    version=0.9,
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
