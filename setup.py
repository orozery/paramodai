#!/usr/bin/python
from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    requires = [x.strip() for x in f if x.strip()]


setup(
    name='paramodai',
    version='0.1',
    description='Paramodulation based Abstract Interpretation',
    author='Or Ozeri',
    packages=find_packages(),
    install_requires=requires,
)