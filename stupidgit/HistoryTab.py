import wx
from CommitList import CommitList, EVT_COMMITLIST_SELECT, EVT_COMMITLIST_RIGHTCLICK
from DiffViewer import DiffViewer
from git import GitError

# Menu item ids
MENU_CREATE_BRANCH      = 10000
MENU_DELETE_BRANCH      = 11000

# This array is used to provide unique ids for menu items
# that refer to a branch
branch_indexes = []

class HistoryTab(wx.Panel):
    def __init__(self, mainWindow, parent, id):
        # Layout
        wx.Panel.__init__(self, parent, id)
        self.mainWindow = mainWindow
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Splitter
        self.splitter = wx.SplitterWindow(self, -1)
        self.sizer.Add(self.splitter, True, wx.EXPAND, wx.ALL)

        # History graph
        self.commitList = CommitList(self.splitter, -1)
        self.Bind(EVT_COMMITLIST_SELECT, self.OnCommitSelected, self.commitList)
        self.Bind(EVT_COMMITLIST_RIGHTCLICK, self.OnCommitRightClick, self.commitList)

        self.diffViewer = DiffViewer(self.splitter, -1)

        self.splitter.SetMinimumPaneSize(20)
        self.splitter.SplitHorizontally(self.commitList, self.diffViewer, 200)

        # Context menu
        self.contextMenu = wx.Menu()
        wx.EVT_MENU(self, MENU_CREATE_BRANCH, self.OnCreateBranch)

    def SetRepo(self, repo):
        # Branch indexes
        global branch_indexes
        for branch in repo.branches:
            if branch not in branch_indexes:
                branch_indexes.append(branch)

                # Menu events
                index = len(branch_indexes)-1
                wx.EVT_MENU(self, MENU_DELETE_BRANCH + index, self.OnDeleteBranch)

        self.repo = repo
        self.commitList.SetRepo(repo)

        difftext = self.repo.run_cmd(['show', 'HEAD^'])
        self.diffViewer.Clear()

    def OnCommitSelected(self, e):
        commit = self.commitList.CommitByRow(e.currentRow)

        # Show in diff viewer
        commit_diff = self.repo.run_cmd(['show', commit.sha1])
        self.diffViewer.SetDiffText(commit_diff, commit_mode=True)

    def OnCommitRightClick(self, e):
        self.contextCommit = self.commitList.CommitByRow(e.currentRow)
        self.SetupContextMenu(self.contextCommit)
        self.commitList.PopupMenu(self.contextMenu, e.coords)

    def OnCreateBranch(self, e):
        dialog = wx.TextEntryDialog(self, "Enter branch name:", "Create branch...")
        if dialog.ShowModal() == wx.ID_OK:
            branch_name = dialog.GetValue()
            try:
                s = self.repo.run_cmd(['branch', branch_name, self.contextCommit.sha1], raise_error=True)
                self.repo.load_refs()
                self.SetRepo(self.repo)
            except GitError, msg:
                wx.MessageBox(str(msg), 'Error', style=wx.OK|wx.ICON_ERROR)

    def OnDeleteBranch(self, e):
        branch = branch_indexes[e.GetId() % 1000]
        msg = wx.MessageDialog(
            self.mainWindow,
            "By deleting branch '%s' all commits that are not referenced by another branch will be lost.\n\nDo you really want to continue?" % branch,
            "Warning",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            try:
                self.repo.run_cmd(['branch', '-d', branch], raise_error=True)
                self.repo.load_refs()
                self.SetRepo(self.repo)
            except GitError, msg:
                wx.MessageBox(str(msg), 'Error', style=wx.OK|wx.ICON_ERROR)

    def SetupContextMenu(self, commit):
        branches = self.repo.branches_by_sha1.get(commit.sha1, [])

        # Delete old items
        menuItems = self.contextMenu.GetMenuItems()
        for item in menuItems:
            self.contextMenu.Delete(item.GetId())

        # Create branch
        self.contextMenu.Append(MENU_CREATE_BRANCH, "Create branch here...")

        # Delete branch
        if branches:
            self.contextMenu.AppendSeparator()

            for branch in branches:
                menu_id = MENU_DELETE_BRANCH + branch_indexes.index(branch)
                self.contextMenu.Append(menu_id, "Delete branch '%s'" % branch)

