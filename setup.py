#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import io
from setuptools import setup

setup(name='comet-cms',
      version='0.6.0',
      description='Getting rid of the dinosaurs (WordPress and friends).',
      keywords='comet',
      author='Chris Warrick and the Comet contributors',
      author_email='chris@getnikola.com',
      url='https://github.com/getnikola/comet_cms',
      license='MIT',
      long_description=io.open('./README.rst', 'r', encoding='utf-8').read(),
      platforms='any',
      zip_safe=False,
      # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=['Development Status :: 2 - Pre-Alpha',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 2',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.3',
                   'Programming Language :: Python :: 3.4'],
      packages=['comet'],
      include_package_data=True,
      entry_points={
          'console_scripts': [
              'comet = comet.__main__:main',
          ]
      },
      )
