#!/usr/bin/env python

from setuptools import setup, find_packages

# The version is updated automatically with bumpversion
# Do not update manually
__version = '1.0.1'

long_description = """
This python module provides classes used by BakeOutControlDS Devices
It provides BakeOutControlDS Tango Device Server
"""


classifiers = [
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'Topic :: Scientific/Engineering',
    'Topic :: Software Development :: Libraries',
    'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
    'Programming Language :: Python :: 2.7',
]

entry_points = {
    'console_scripts': [
        'BakeOutControlDS = BakeOutControlDS.BakeOutControlDS:main',
        ]
}

scripts = [ 'bin/BakeOutControlDS' ]

setup(
    name='BakeOutControlDS',
    version=__version,
    include_package_data=True,
    packages=find_packages(),
    #entry_points=entry_points,
    scripts=scripts,
    author='Sergi Rubio',
    author_email='srubio@cells.es',
    maintainer='srubio',
    maintainer_email='srubio@cells.es',
    url='https://git.cells.es/controls/BakeOutControlDS',
    keywords='APP',
    license='LGPL',
    description='BakeOutControlDS Tango Device Server',
    long_description=long_description,
    requires=['setuptools (>=1.1)'],
    install_requires=['python-numpy', 'python-tango', 'python-fandango'],
    classifiers=classifiers
)
