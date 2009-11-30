import wx
import os
import os.path
from CommitList import CommitList, EVT_COMMITLIST_SELECT, EVT_COMMITLIST_RIGHTCLICK
from DiffViewer import DiffViewer
from SwitchWizard import SwitchWizard
from Wizard import *
from FetchDialogs import FetchSetupDialog, FetchProgressDialog
import git
from git import GitError
from util import *

# Menu item ids
MENU_SWITCH_TO_COMMIT   = 10000
MENU_MERGE_COMMIT       = 10001
MENU_CHERRYPICK_COMMIT  = 10002
MENU_REVERT_COMMIT      = 10003
MENU_FETCH_COMMITS      = 10004

MENU_CREATE_BRANCH      = 11000
MENU_DELETE_BRANCH      = 12000

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
        wx.EVT_MENU(self, MENU_SWITCH_TO_COMMIT, self.OnSwitchToCommit)
        wx.EVT_MENU(self, MENU_CREATE_BRANCH, self.OnCreateBranch)
        wx.EVT_MENU(self, MENU_MERGE_COMMIT, self.OnMerge)
        wx.EVT_MENU(self, MENU_CHERRYPICK_COMMIT, self.OnCherryPick)
        wx.EVT_MENU(self, MENU_REVERT_COMMIT, self.OnRevert)
        wx.EVT_MENU(self, MENU_FETCH_COMMITS, self.OnFetch)

    def SetRepo(self, repo):
        # Branch indexes
        global branch_indexes
        for branch in repo.branches:
            if branch not in branch_indexes:
                branch_indexes.append(branch)

        # Menu events for branches
        for index in xrange(len(branch_indexes)):
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

    def OnSwitchToCommit(self, e):
        wizard = SwitchWizard(self.mainWindow, -1, self.repo, self.contextCommit)
        result = wizard.RunWizard()

        if result > 0:
            self.mainWindow.ReloadRepo()

            # Check for unmerged changes
            unmerged = False
            unstaged, staged = self.repo.get_status()
            for f in unstaged:
                if unstaged[f] == git.FILE_UNMERGED:
                    unmerged = True

            # Show error if checkout failed
            if wizard.error:
                wx.MessageBox(safe_unicode(wizard.error), 'Could not switch to this version', style=wx.OK|wx.ICON_ERROR)
                return

            # Show warning if necessary
            msg = ''
            if unmerged:
                msg = u'- Repository contains unmerged files. You have to merge them manually.'

            if wizard.submoduleWarnings:
                submodules = wizard.submoduleWarnings.keys()
                submodules.sort()

                if msg:
                    msg += '\n- '

                if len(submodules) == 1:
                    submodule = submodules[0]
                    msg += u"Submodule '%s' could not be switched to the referenced version:%s" \
                        % (submodule, safe_unicode(wizard.submoduleWarnings[submodule]))
                else:
                    msg += u"Some submodules could not be switched to the referenced version:\n\n"
                    for submodule in submodules:
                        msg += u"  - %s: %s\n" % (submodule, safe_unicode(wizard.submoduleReasons[submodule]))

            if msg:
                if len(msg.split('\n')) == 1:
                    msg = msg[2:] # remove '- ' from the beginning

                wx.MessageBox(msg, 'Warning', style=wx.OK|wx.ICON_ERROR)

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
                        "Some files or submodules could not be automatically cherry-picked. " + \
                        "You have to resolve these conflicts by hand and then stage " + \
                        "these files/submodules.\n\n" + \
                        "If you want to abort cherry-picking, press \"Discard all changes\" on Index page."
                else:
                    warningTitle = "Error"
                    warningMsg = "Git returned the following error:\n\n" + stdout + stderr

                wx.MessageBox(warningMsg, warningTitle, style=wx.OK|wx.ICON_ERROR)

    def OnRevert(self, e):
        confirmMsg = "Do you really want to revert this commit?"
        msg = wx.MessageDialog(
            self.mainWindow,
            confirmMsg,
            "Confirmation",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            retcode, stdout, stderr = self.repo.run_cmd(['revert', self.contextCommit.sha1], with_retcode=True, with_stderr=True)
            self.mainWindow.ReloadRepo()

            if retcode != 0:
                if 'Automatic reverting failed' in stderr:
                    warningTitle = "Warning: conflicts during reverting"
                    warningMsg = \
                        "Some files or submodules could not be automatically reverted. " + \
                        "You have to resolve these conflicts by hand and then stage " + \
                        "these files/submodules.\n\n" + \
                        "If you want to abort reverting, press \"Discard all changes\" on Index page."
                else:
                    warningTitle = "Error"
                    warningMsg = "Git returned the following error:\n\n" + stdout + stderr

                wx.MessageBox(warningMsg, warningTitle, style=wx.OK|wx.ICON_ERROR)

    def OnFetch(self, e):
        # Setup dialog
        setupDialog = FetchSetupDialog(self, -1, self.repo)
        result = setupDialog.ShowModal()

        # Progress dialog
        if result:
            progressDialog = FetchProgressDialog(self, -1, self.repo, setupDialog.selectedRemote)
            if progressDialog.ShowModal():
                self.mainWindow.ReloadRepo()

    def OnFetchProgress(self, eventType, eventParam):
        print 'FETCH CALLBACK:', eventType, eventParam

    def SetupContextMenu(self, commit):
        branches = self.repo.branches_by_sha1.get(commit.sha1, [])

        # Delete old items
        menuItems = self.contextMenu.GetMenuItems()
        for item in menuItems:
            self.contextMenu.Delete(item.GetId())

        # Switch to this version...
        self.contextMenu.Append(MENU_SWITCH_TO_COMMIT, "Switch to this version...")

        # Create branch
        self.contextMenu.Append(MENU_CREATE_BRANCH, "Create branch here...")

        # Delete branch
        if branches:
            self.contextMenu.AppendSeparator()

            for branch in branches:
                menu_id = MENU_DELETE_BRANCH + branch_indexes.index(branch)
                self.contextMenu.Append(menu_id, "Delete branch '%s'" % branch)

        # Merge
        self.contextMenu.AppendSeparator()
        self.contextMenu.Append(MENU_MERGE_COMMIT, "Merge into current HEAD")

        # Cherry-pick
        self.contextMenu.Append(MENU_CHERRYPICK_COMMIT, "Pick this commit to HEAD (cherry-pick)")
        self.contextMenu.Append(MENU_REVERT_COMMIT, "Pick the inverse of this commit to HEAD (revert)")

        # Fetch, push
        if self.repo.remotes:
            self.contextMenu.AppendSeparator()
            self.contextMenu.Append(MENU_FETCH_COMMITS, "Fetch commits from remote repository")

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

