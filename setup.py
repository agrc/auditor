#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
setup.py
A module that installs auditor as a module
"""
from glob import glob
from os.path import basename, splitext

from setuptools import find_packages, setup

setup(
    name="auditor",
    version="3.0.2",
    license="MIT",
    description=(
        "Audits all hosted feature service items in a user's AGOL folders for proper tags, sharing, etc based on "
        "an external metatable"
    ),
    author="Jake Adams",
    author_email="jdadams@utah.gov",
    url="https://github.com/agrc/auditor",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    zip_safe=True,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: System Administrators",
        "Topic :: Utilities",
    ],
    project_urls={
        "Issue Tracker": "https://github.com/agrc/auditor/issues",
    },
    keywords=["gis"],
    install_requires=[
        "docopt==0.6.*",
        "arcgis==2.*",
        "agrc-supervisor==3.*",
    ],
    extras_require={
        "tests": [
            "pytest-cov>=3,<6",
            "pytest-instafail==0.5.*",
            "pytest-mock==3.*",
            "pytest-ruff==0.*",
            "pytest-watch==4.*",
            "pytest>=6,<9",
            "black>=23.3,<24.5",
            "ruff==0.0.*",
            "pytest-mock>=3.10,<3.15",
        ]
    },
    setup_requires=[
        "pytest-runner",
    ],
    entry_points={"console_scripts": ["auditor = auditor.cli:cli"]},
)
