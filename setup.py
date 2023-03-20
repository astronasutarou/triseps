#!/usr/bin/env python
# -*- coding: utf-8 -*-
from glob import glob
from setuptools import setup, find_packages
import os, sys, re


from tricceps import __version__


with open('README.md', 'r') as fd:
  version = __version__
  author = 'Ryou Ohsawa'
  email = 'ryou.ohsawa@nao.ac.jp'
  description = ''
  long_description = fd.read()
  license = 'MIT'


with open('requirements.txt','r') as fd:
  requirements = fd.read().splitlines()


classifiers = [
  'Development Status :: 3 - Alpha',
  'Environment :: Console',
  'Intended Audience :: Science/Research',
  'License :: OSI Approved :: MIT License',
  'Operating System :: POSIX :: Linux',
  'Programming Language :: Python :: 3',
  'Programming Language :: Python :: 3.7',
  'Topic :: Scientific/Engineering :: Astronomy'
]


if __name__ == '__main__':
  setup(
    name='tricceps',
    version=version,
    author=author,
    author_email=email,
    maintainer=author,
    maintainer_email=email,
    description=description,
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='',
    license=license,
    packages=find_packages(),
    classifiers=classifiers,
    install_requires=requirements)

