#!/usr/bin/env python
# -*- coding: utf-8

import sys
import os
import os.path
import wx

# Add module path .. if ../stupidgit exists
curfile = __file__
if os.path.islink(curfile):
    curfile = os.path.abspath(os.readlink(curfile))
curdir = os.path.dirname(curfile)
moduledir = os.path.abspath(os.path.join(curdir, '..', 'stupidgit'))
if os.path.isdir(moduledir):
    sys.path.insert(0, os.path.dirname(moduledir))

# Load stupidgit module
from stupidgit import *

# Parse arguments
repodir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

# Show main window
try:
    repo = Repository(repodir)
except GitError:
    repo = None
app = wx.PySimpleApp()
win = MainWindow(None, -1, repo)
win.Show(True)
app.MainLoop()
