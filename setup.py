"""
py2app/py2exe build script for stupidgit.

Usage (Mac OS X):
    python setup.py py2app

Usage (Windows):
    python setup.py py2exe
"""
import sys
import os
import distutils.core
import distutils.command.install

if sys.platform == 'darwin':
    from setuptools import setup
else:
    from distutils.core import setup

if sys.platform == 'darwin':
    extra_options = dict(
        setup_requires=['py2app'],
        app=['stupidgit_gui/run.py'],
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

    if sys.version >= '2.6':
        print "Due to a py2exe bug StupidGit can be built only from Python 2.5!"
        os.exit()

    # Workaround py2exe bug
    origIsSystemDLL = py2exe.build_exe.isSystemDLL

    def isSystemDLL(pathname):
        if os.path.basename(pathname).lower() in ("msvcp71.dll", "dwmapi.dll"):
            return 0
        return origIsSystemDLL(pathname)

    py2exe.build_exe.isSystemDLL = isSystemDLL

    extra_options = dict(
        setup_requires=['py2exe'],
        windows=[{
            'script': 'bin/stupidgit',
            'icon_resources': [(0,'icon/icon.ico')],
            'dest_base': 'stupidgit'
        }],
    )
elif os.name == 'posix':
    extra_options = dict(
        data_files = [
            ('/usr/share/stupidgit', ['icon/icon_48x48.png']),
            ('/usr/share/applications', ['stupidgit.desktop'])
        ]
    )
else:
    extra_options=dict()

setup(
    name='StupidGit',
    version='0.1.1',
    description='A cross-platform git GUI with strong support for submodules',
    author='Akos Gyimesi',
    author_email='gyimesi.akos@gmail.com',
    packages=['stupidgit_gui'],
    scripts=['bin/stupidgit'],

    **extra_options
)

