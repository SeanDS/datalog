#!/usr/bin/env python3

from setuptools import setup
import datalog

with open("README.md") as readme_file:
    readme = readme_file.read()

__version__ = datalog.__version__

requirements = [
    "appdirs"
]

setup(
    name="datalog",
    version=__version__,
    description="Python library to interface with PicoLog ADC hardware",
    long_description=readme,
    author="Sean Leavey",
    author_email="datalog@attackllama.com",
    url="https://github.com/SeanDS/datalog",
    packages=[
        "datalog",
        "datalog.adc",
        "datalog.adc.hrdl"
    ],
    package_data={
        "datalog.adc": ['adc.conf.dist']
    },
    install_requires=requirements,
    license="GPLv3",
    zip_safe=False,
    classifiers=[
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5"
    ]
)
