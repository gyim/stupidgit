#!/usr/bin/env python
# -*- coding: utf-8

import sys
import os
import os.path
import wx

from git import Repository
from MainWindow import *

def main():
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

if __name__ == '__main__':
    main()

