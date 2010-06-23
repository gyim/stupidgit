import wx
from MainWindow import *
from wxutil import *

class HiddenWindow(object):
    def __init__(self):
        super(HiddenWindow, self).__init__()
        self.frame = LoadFrame(None, 'HiddenWindow')
        
        SetupEvents(self.frame, [
            (None, wx.EVT_CLOSE, self.OnWindowClosed),
            ('quitMenuItem', wx.EVT_MENU, self.OnExit),
            ('openMenuItem', wx.EVT_MENU, self.OnOpenRepository),
            ('newWindowMenuItem', wx.EVT_MENU, self.OnNewWindow),
        ])
    
    def ShowMenu(self):
        self.frame.SetPosition((-10000,-10000))
        self.frame.Show()
        self.frame.Hide()

    def OnWindowClosed(self, e):
        # Do nothing
        pass

    def OnNewWindow(self, e):
        win = MainWindow(None)
        win.Show(True)

    def OnOpenRepository(self, e):
        repodir = wx.DirSelector("Open repository")
        if not repodir: return

        try:
            repo = Repository(repodir)
            new_win = MainWindow(repo)
            new_win.Show(True)
        except GitError, msg:
            wx.MessageBox(str(msg), 'Error', style=wx.OK|wx.ICON_ERROR)

    def OnExit(self, e):
        wx.TheApp.ExitApp()

