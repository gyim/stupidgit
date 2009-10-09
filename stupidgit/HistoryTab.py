import wx
import os
import os.path
from CommitList import CommitList, EVT_COMMITLIST_SELECT, EVT_COMMITLIST_RIGHTCLICK
from DiffViewer import DiffViewer
from Wizard import *
import git
from git import GitError

# Menu item ids
MENU_CHECKOUT_DETACHED  = 10000
MENU_RESET_BRANCH       = 10001
MENU_MERGE_COMMIT       = 10002
MENU_CHERRYPICK_COMMIT  = 10003

MENU_CREATE_BRANCH      = 11000
MENU_DELETE_BRANCH      = 12000
MENU_CHECKOUT_BRANCH    = 13000

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
        self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_LIVE_UPDATE)
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
        wx.EVT_MENU(self, MENU_CHECKOUT_DETACHED, self.OnCheckout)
        wx.EVT_MENU(self, MENU_RESET_BRANCH, self.OnResetBranch)
        wx.EVT_MENU(self, MENU_MERGE_COMMIT, self.OnMerge)
        wx.EVT_MENU(self, MENU_CHERRYPICK_COMMIT, self.OnCherryPick)

    def SetRepo(self, repo):
        # Branch indexes
        global branch_indexes
        for branch in repo.branches:
            if branch not in branch_indexes:
                branch_indexes.append(branch)

                # Menu events
                index = len(branch_indexes)-1
                wx.EVT_MENU(self, MENU_DELETE_BRANCH + index, self.OnDeleteBranch)
                wx.EVT_MENU(self, MENU_CHECKOUT_BRANCH + index, self.OnCheckout)

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
            self.GitCommand(['branch', branch_name, self.contextCommit.sha1])

    def OnDeleteBranch(self, e):
        branch = branch_indexes[e.GetId() % 1000]
        msg = wx.MessageDialog(
            self.mainWindow,
            "By deleting branch '%s' all commits that are not referenced by another branch will be lost.\n\nDo you really want to continue?" % branch,
            "Warning",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            self.GitCommand(['branch', '-D', branch])

    def OnCheckout(self, e):
        if e.GetId() == MENU_CHECKOUT_DETACHED:
            checkout_target = self.contextCommit.sha1
            confirmMsg = "Do you really want to checkout this commit as detached HEAD?"
        else:
            branch = branch_indexes[e.GetId() % 1000]
            checkout_target = branch
            confirmMsg = "Do you really want to checkout branch '%s'?" % branch

        msg = wx.MessageDialog(
            self.mainWindow,
            confirmMsg,
            "Confirmation",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            self.GitCommand(['checkout', checkout_target], True)

    def OnResetBranch(self, e):
        wizard = ResetWizard(self.mainWindow, -1, self.repo)
        if wizard.RunWizard():
            resetTypes = ['--soft', '--mixed', '--hard']
            resetType = resetTypes[wizard.resetType]
            self.GitCommand(['reset', resetType, self.contextCommit.sha1], True)

    def OnMerge(self, e):
        # Default merge message
        if self.repo.current_branch:
            local_branch = self.repo.current_branch
        else:
            local_branch = "HEAD"

        remote_sha1 = self.contextCommit.sha1
        if remote_sha1 in self.repo.branches_by_sha1:
            remote_branch = "branch '%s'" % self.repo.branches_by_sha1[remote_sha1][0]
        elif remote_sha1 in self.repo.remote_branches_by_sha1:
            remote_branch = "remote branch '%s'" % self.repo.remote_branches_by_sha1[remote_sha1][0]
        else:
            remote_branch = "commit '%s'" % self.contextCommit.abbrev

        mergeMsg = "merge %s into %s" % (remote_branch, local_branch)

        # Show merge message dialog
        msg = wx.TextEntryDialog(
            self.mainWindow,
            "Enter merge message:",
            "Merge",
            mergeMsg,
            wx.ICON_QUESTION | wx.OK | wx.CANCEL
        )
        if msg.ShowModal() == wx.ID_OK:
            retcode, stdout, stderr = self.repo.run_cmd(['merge', self.contextCommit.sha1, '-m', mergeMsg], with_retcode=True, with_stderr=True)
            self.mainWindow.ReloadRepo()

            if retcode != 0:
                if 'CONFLICT' in stdout:
                    # Create MERGE_MSG
                    f = open(os.path.join(self.repo.dir, '.git', 'MERGE_MSG'), 'w')
                    f.write("%s\n\nConflicts:\n" % mergeMsg)
                    unstaged, staged = self.repo.get_status()
                    unmerged_files = [ fn for fn,status in unstaged.iteritems() if status == git.FILE_UNMERGED ]
                    for fn in unmerged_files:
                        f.write("\t%s\n" % fn)
                    f.close()

                    # Show warning
                    warningTitle = "Warning: conflicts during merge"
                    warningMsg = \
                        "Some files or submodules could not be automatically merged. " + \
                        "You have to resolve these conflicts by hand and then stage " + \
                        "these files/submodules.\n\n" + \
                        "If you want to abort merge, press \"Discard all changes\" on Index page."
                else:
                    warningTitle = "Error"
                    warningMsg = "Git returned the following error:\n\n" + stdout + stderr

                wx.MessageBox(warningMsg, warningTitle, style=wx.OK|wx.ICON_ERROR)

    def OnCherryPick(self, e):
        confirmMsg = "Do you really want to cherry-pick this commit?"
        msg = wx.MessageDialog(
            self.mainWindow,
            confirmMsg,
            "Confirmation",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            retcode, stdout, stderr = self.repo.run_cmd(['cherry-pick', self.contextCommit.sha1], with_retcode=True, with_stderr=True)
            self.mainWindow.ReloadRepo()

            if retcode != 0:
                if 'Automatic cherry-pick failed' in stderr:
                    warningTitle = "Warning: conflicts during cherry-picking"
                    warningMsg = \
                        "Some files or submodulues could not be automatically cherry-picked. " + \
                        "You have to resolve these conflicts by hand and then stage " + \
                        "these files/submodules.\n\n" + \
                        "If you want to abort cherry-picking, press \"Discard all changes\" on Index page."
                else:
                    warningTitle = "Error"
                    warningMsg = "Git returned the following error:\n\n" + stdout + stderr

                wx.MessageBox(warningMsg, warningTitle, style=wx.OK|wx.ICON_ERROR)

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

        # Checkout
        self.contextMenu.AppendSeparator()
        if branches:
            for branch in branches:
                menu_id = MENU_CHECKOUT_BRANCH + branch_indexes.index(branch)
                self.contextMenu.Append(menu_id, "Checkout branch '%s'" % branch)

        self.contextMenu.Append(MENU_CHECKOUT_DETACHED, "Checkout as detached HEAD")

        # Reset branch
        if self.repo.current_branch:
            self.contextMenu.AppendSeparator()
            self.contextMenu.Append(MENU_RESET_BRANCH, "Reset branch '%s' here" % self.repo.current_branch)

        # Merge
        self.contextMenu.AppendSeparator()
        self.contextMenu.Append(MENU_MERGE_COMMIT, "Merge into current HEAD")

        # Cherry-pick
        self.contextMenu.Append(MENU_CHERRYPICK_COMMIT, "Cherry-pick this commit")

    def GitCommand(self, cmd, check_submodules=False, **opts):
        try:
            retval = self.repo.run_cmd(cmd, raise_error=True, **opts)
            self.mainWindow.ReloadRepo()

            # Check submodules
            if check_submodules and self.repo.submodules:
                for submodule in self.repo.submodules:
                    if submodule.main_ref != submodule.head:
                        wx.MessageBox(
                            "One or more submodule versions differ from the version " +
                            "that is referenced by the current HEAD. If this is not " +
                            "what you want, you need to checkout them to the proper version.",
                            'Warning',
                            style=wx.OK|wx.ICON_WARNING
                        )
                        break

            return retval
        except GitError, msg:
            wx.MessageBox(str(msg), 'Error', style=wx.OK|wx.ICON_ERROR)
            return False

class ResetWizard(Wizard):
    def __init__(self, parent, id, repo):
        Wizard.__init__(self, parent, id)
        self.repo = repo

        # Choose reset type page
        self.typePage = self.CreatePage(
            "Choose reset type",
            [BTN_CANCEL, BTN_CONTINUE]
        )

        font = wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.BOLD) 
        self.typePageCaption = wx.StaticText(self.typePage, -1, "Choose reset type")
        self.typePageCaption.SetFont(font)
        self.typePage.sizer.Add(self.typePageCaption, 0, wx.EXPAND | wx.ALL, 10)

        self.typeBtns = wx.RadioBox(self.typePage, -1, "", 
            style=wx.RA_SPECIFY_ROWS,
            choices=[
                "Soft reset: keep working directory and index untouched",
                "Mixed reset: preserve working directory, reset index",
                "Hard reset: discard ALL changes"
            ]
        )

        self.typePage.sizer.Add(self.typeBtns, 1, wx.EXPAND | wx.ALL, 10)

        # Warning page
        self.warningPage = self.CreateWarningPage(
            "Warning: you may lose commits",

            ("You are about to reset the current branch (%s) to a different version. " +
            "All commits that are not referenced by another branch, tag or " +
            "remote branch will be lost.\n\n" +
            "Do you really want to continue?") % self.repo.current_branch,

            [BTN_CANCEL, BTN_FINISH]
        )

    def OnStart(self):
        self.SetPage(self.typePage)

    def OnButtonClicked(self, button):
        if button == BTN_CONTINUE:
            self.resetType = self.typeBtns.GetSelection()
            self.SetPage(self.warningPage)
        if button == BTN_CANCEL:
            self.EndWizard(0)
        if button == BTN_FINISH:
            self.EndWizard(1)
