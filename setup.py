"""
py2app/py2exe build script for stupidgit.

Usage (Mac OS X):
    python setup.py py2app

Usage (Windows):
    python setup.py py2exe
"""
import sys
from setuptools import setup

mainscript = 'bin/run.py'

if sys.platform == 'darwin':
    extra_options = dict(
        setup_requires=['py2app'],
        app=[mainscript],
        # Cross-platform applications generally expect sys.argv to
        # be used for opening files.
        options=dict(
            py2app=dict(
                packages='wx',
                site_packages=True,
                argv_emulation=True
            )
        ),
    )
elif sys.platform == 'win32':
    import py2exe
    extra_options = dict(
        setup_requires=['py2exe'],
        windows=[mainscript],
    )
else:
     extra_options = dict(
         # Normally unix-like platforms will use "setup.py install"
         # and install the main script as such
         scripts=[mainscript],
     )

setup(
    name='stupidgit',
    version='0.1',
    description='A cross-platform git GUI with strong support for submodules',
    author='Akos Gyimesi',
    author_email='gyimesi.akos@gmail.com',
    packages=['stupidgit'],

    **extra_options
)

