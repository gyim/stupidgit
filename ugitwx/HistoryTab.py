import wx
from CommitList import CommitList

class HistoryTab(wx.Panel):
    def __init__(self, mainWindow, parent, id):
        wx.Panel.__init__(self, parent, id)
        self.mainWindow = mainWindow
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.commitList = CommitList(self, -1)
        self.sizer.Add(self.commitList, True, wx.EXPAND, wx.ALL)

    def SetRepo(self, repo):
        self.repo = repo
        self.commitList.SetRepo(repo)

