#!/usr/bin/env python
# -*- coding: utf-8

import sys
import os
import os.path
import wx

from git import Repository
from MainWindow import *
from PasswordDialog import *
from HiddenWindow import *

class StupidGitApp(wx.PySimpleApp):
    def InitApp(self):
        self.SetAppName('StupidGit')
        wx.TheApp = self
        self.app_windows = []
        if sys.platform == 'darwin':
            self.hiddenWindow = HiddenWindow()
            self.SetExitOnFrameDelete(False)
            wx.App_SetMacAboutMenuItemId(xrc.XRCID('aboutMenuItem'))
            wx.App_SetMacExitMenuItemId(xrc.XRCID('quitMenuItem'))
        
    def OpenRepo(self, repo=None):
        # Find the first empty window (if exists)
        win = None
        for app_window in self.app_windows:
            if not app_window.mainRepo:
                win = app_window
                break
        
        if win:
            # Open repository in existing empty window
            win.SetMainRepo(repo)
        else:
            # Create a new window
            win = MainWindow(repo)
            win.Show(True)
    
    def OnWindowCreated(self, win):
        self.app_windows.append(win)
    
    def OnWindowClosed(self, win):
        self.app_windows.remove(win)
        if len(self.app_windows) == 0:
            self.hiddenWindow.ShowMenu()
    
    def ExitApp(self):
        while self.app_windows:
            self.app_windows[0].frame.Close(True)
        self.ExitMainLoop()
    
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

