#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

def read_requirements(filename):
    with open(filename, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


PACKAGE_EXCLUDES = [
]

PACKAGE_INCLUDES = [
    "swellnet",
]


setup(
    name='swellnet',
    version='0.1.0',
    description='Toolboxes for handling swellnet data',
    author='Thiago Caminha',
    author_email='thiago.caminha@uwa.edu.au',
    url='',
    install_requires=read_requirements('requirements.txt'),
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    python_requires='>3.8'
)
