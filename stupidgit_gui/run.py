#!/usr/bin/env python
# -*- coding: utf-8

import sys
import os
import os.path
import wx

from git import Repository
from MainWindow import *
from PasswordDialog import *

class StupidGitApp(wx.App):
    def InitApp(self):
        self.SetAppName('StupidGit')
        wx.TheApp = self
        if sys.platform == 'darwin':
            self.SetExitOnFrameDelete(False)
        
    def OpenRepo(self, repo=None):
        win = MainWindow(repo)
        win.Show(True)
    
    def MacOpenFile(self, filename):
        try:
            repo = Repository(filename)
            self.OpenRepo(repo)
        except GitError:
            pass

def main_normal():
    # Parse arguments
    repodir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    # Show main window
    try:
        repo = Repository(repodir)
    except GitError:
        repo = None
    
    app = StupidGitApp()
    app.InitApp()
    app.OpenRepo(repo)
    app.MainLoop()

def main_askpass():
    app = wx.PySimpleApp()

    askpass = PasswordDialog(None, -1, ' '.join(sys.argv[1:]))
    askpass.ShowModal()

    if askpass.password:
        print askpass.password
        sys.exit(0)
    else:
        sys.exit(1)

def main():
    if 'askpass' in sys.argv[0]:
        main_askpass()
    else:
        main_normal()

if __name__ == '__main__':
    main()

