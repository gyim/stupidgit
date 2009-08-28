import wx
from CommitList import CommitList, EVT_COMMITLIST_SELECT
from DiffViewer import DiffViewer

class HistoryTab(wx.Panel):
    def __init__(self, mainWindow, parent, id):
        wx.Panel.__init__(self, parent, id)
        self.mainWindow = mainWindow
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.splitter = wx.SplitterWindow(self, -1)
        self.sizer.Add(self.splitter, True, wx.EXPAND, wx.ALL)

        self.commitList = CommitList(self.splitter, -1)
        self.Bind(EVT_COMMITLIST_SELECT, self.OnCommitSelected, self.commitList)

        self.diffViewer = DiffViewer(self.splitter, -1)

        self.splitter.SetMinimumPaneSize(20)
        self.splitter.SplitHorizontally(self.commitList, self.diffViewer, 200)

    def SetRepo(self, repo):
        self.repo = repo
        self.commitList.SetRepo(repo)

        difftext = self.repo.run_cmd(['show', 'HEAD^'])
        self.diffViewer.Clear()

    def OnCommitSelected(self, e):
        commit = self.commitList.CommitByRow(e.currentRow)

        # Show in diff viewer
        commit_diff = self.repo.run_cmd(['show', commit.sha1])
        self.diffViewer.SetDiffText(commit_diff, commit_mode=True)

