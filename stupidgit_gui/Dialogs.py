import wx
import wx.lib.mixins.listctrl as listmixins
import git

from DiffViewer import DiffViewer
from IndexTab import MOD_DESCS
from util import *

class AutosizedListCtrl(wx.ListCtrl, listmixins.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmixins.ListCtrlAutoWidthMixin.__init__(self)

class DiffDialog(wx.Dialog):
    def __init__(self, parent, id, title='', message=''):
        wx.Dialog.__init__(self, parent, id, size=(600,600), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetTitle(title)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Splitter
        self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_LIVE_UPDATE)
        self.sizer.Add(self.splitter, True, wx.EXPAND, wx.ALL)

        self.topPanel = wx.Panel(self.splitter, -1)
        self.topSizer = wx.BoxSizer(wx.VERTICAL)
        self.topPanel.SetSizer(self.topSizer)

        self.bottomPanel = wx.Panel(self.splitter, -1)
        self.bottomSizer = wx.BoxSizer(wx.VERTICAL)
        self.bottomPanel.SetSizer(self.bottomSizer)

        # Message
        self.messageTxt = wx.StaticText(self.topPanel, -1, message)
        self.topSizer.Add(self.messageTxt, 0, wx.EXPAND | wx.ALL, 5)

        # List
        self.listCtrl = AutosizedListCtrl(self.topPanel, -1, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.listCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnListItemSelected)
        self.topSizer.Add(self.listCtrl, 1, wx.EXPAND | wx.ALL, 5)

        # DiffViewer
        self.diffViewer = DiffViewer(self.bottomPanel, -1)
        self.bottomSizer.Add(self.diffViewer, 1, wx.EXPAND | wx.ALL, 5)

        # Close button
        self.closeButton = wx.Button(self.bottomPanel, -1, 'Close')
        self.closeButton.Bind(wx.EVT_BUTTON, self.OnClose)
        self.bottomSizer.Add(self.closeButton, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Layout
        self.splitter.SetMinimumPaneSize(200)
        self.splitter.SplitHorizontally(self.topPanel, self.bottomPanel, 250)

    def SetMessage(self, message):
        self.messageTxt.SetLabel(message)

    def OnListItemSelected(self, e):
        pass

    def OnClose(self, e):
        self.EndModal(0)

class CommitListDialog(DiffDialog):
    def __init__(self, parent, id, repo, commits, title='', message=''):
        DiffDialog.__init__(self, parent, id, title, message)
        self.repo = repo
        self.commits = commits

        # Setup list control
        self.listCtrl.InsertColumn(0, "Author")
        self.listCtrl.InsertColumn(1, "Commit message")
        self.listCtrl.InsertColumn(2, "Date")

        self.listCtrl.SetColumnWidth(0, 150)
        self.listCtrl.SetColumnWidth(1, 300)
        self.listCtrl.SetColumnWidth(2, wx.LIST_AUTOSIZE)

        # Fill list control
        n = 0
        for commit in commits:
            self.listCtrl.InsertStringItem(n, commit.author_name)
            self.listCtrl.SetStringItem(n, 1, commit.short_msg)
            self.listCtrl.SetStringItem(n, 2, commit.author_date)
            n += 1

    def OnListItemSelected(self, e):
        rowid = e.GetIndex()
        commit = self.commits[rowid]

        commit_diff = self.repo.run_cmd(['show', commit.sha1])
        self.diffViewer.SetDiffText(commit_diff, commit_mode=True)

class UncommittedFilesDialog(DiffDialog):
    def __init__(self, parent, id, repo, title='', message=''):
        DiffDialog.__init__(self, parent, id, title, message)
        self.repo = repo

        # Get status
        self.status = repo.get_unified_status()
        self.files = self.status.keys()
        self.files.sort()

        # Setup list control
        self.listCtrl.InsertColumn(0, "Filename")
        self.listCtrl.InsertColumn(1, "Modification")

        self.listCtrl.SetColumnWidth(0, 500)
        self.listCtrl.SetColumnWidth(1, wx.LIST_AUTOSIZE)

        # Fill list control
        n = 0
        for file in self.files:
            self.listCtrl.InsertStringItem(n, file)
            self.listCtrl.SetStringItem(n, 1, MOD_DESCS[self.status[file]])
            n += 1

    def OnListItemSelected(self, e):
        rowid = e.GetIndex()
        file = self.files[rowid]

        if self.status[file] == git.FILE_UNTRACKED:
            commit_diff = git.diff_for_untracked_file(os.path.join(self.repo.dir, file))
        else:
            commit_diff = self.repo.run_cmd(['diff', 'HEAD', file])

        self.diffViewer.SetDiffText(commit_diff, commit_mode=False)

