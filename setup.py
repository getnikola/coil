#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import io
from setuptools import setup

with open('requirements.txt', 'r') as fh:
    dependencies = [l.strip() for l in fh]

setup(name='coil',
      version='1.3.10',
      description='A user-friendly CMS frontend for Nikola.',
      keywords='coil,nikola,cms',
      author='Chris Warrick, Roberto Alsina, Henry Hirsch et al.',
      author_email='chris@getnikola.com',
      url='https://github.com/getnikola/coil',
      license='MIT',
      long_description=io.open('./README.rst', 'r', encoding='utf-8').read(),
      platforms='any',
      zip_safe=False,
      # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=['Development Status :: 7 - Inactive',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.3',
                   'Programming Language :: Python :: 3.4',
                   'Programming Language :: Python :: 3.5',
                   'Programming Language :: Python :: 3.6',
                   ],
      packages=['coil'],
      install_requires=dependencies,
      include_package_data=True,
      entry_points={
          'console_scripts': [
              'coil = coil.__main__:main',
          ]
      },
      )
