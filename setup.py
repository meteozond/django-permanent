#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name='django-permanent',
    version='2.0.0',
    description='Yet another approach to provide soft (logical) delete or masking (thrashing) django models instead of deleting them physically from db.',
    author='Alexander Klimenko',
    author_email='alex@erix.ru',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/meteozond/django-permanent',
    packages=find_packages(),
    install_requires=["Django>=4.2,<6.0"],
    python_requires='>=3.10',
    keywords=['django', 'delete', 'undelete', 'safedelete', 'remove', 'restore', 'softdelete', 'logicaldelete', 'trash'],
    classifiers=[
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.0",
        "Framework :: Django :: 5.1",
        "Framework :: Django :: 5.2",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: BSD License",
    ],
    # Modern approach - use extras_require instead of tests_require
    extras_require={
        'test': [
            'coverage>=7.0',
            'flake8>=6.0',
        ],
        'dev': [
            'coverage>=7.0',
            'flake8>=6.0',
            'coveralls>=3.3',
        ],
    },
    license="BSD"
)
