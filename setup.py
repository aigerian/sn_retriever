__author__ = '4ikist'
from distutils.core import setup
import py2exe

setup(
    windows=[{'script': 'client.py'}],
    options={
        'py2exe': {'includes': ['lxml.etree', 'lxml._elementpath', 'gzip', 'facebook', 'requests'],
                   'compressed': True}},
)
