#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
setup.py
A module that installs agol-validator as a module
"""
from glob import glob
from os.path import basename, splitext

from setuptools import find_packages, setup

setup(
    name='agol-validator',
    version='0.9.0',
    license='MIT',
    description='Validates all hosted feature service items in a user\'s AGOL folders',
    author='Jake Adams',
    author_email='jdadams@utah.gov',
    url='https://github.com/agrc/agol-validator',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=True,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'Topic :: Utilities',
    ],
    project_urls={
        'Issue Tracker': 'https://github.com/agrc/agol-validator/issues',
    },
    keywords=['gis'],
    install_requires=[
        # 'package==1.0.*'
        'docopt==0.6.*'
    ],
    extras_require={
        'tests': [
            'pylint-quotes==0.2.*',
            'pylint==2.5.*',
            'pytest-cov==2.9.*',
            'pytest-instafail==0.4.*',
            'pytest-isort==1.0.*',
            'pytest-pylint==0.17.*',
            'pytest-watch==4.2.*',
            'pytest==5.4.*',
            'yapf==0.30.*',
        ]
    },
    setup_requires=[
        'pytest-runner',
    ],
    entry_points={'console_scripts': [
        'agol-validator = validator.main:cli',
    ]},
)