import wx
import os
import os.path
import MainWindow
from CommitList import CommitList, EVT_COMMITLIST_SELECT, EVT_COMMITLIST_RIGHTCLICK
from DiffViewer import DiffViewer
from SwitchWizard import SwitchWizard
from Wizard import *
from FetchDialogs import FetchSetupDialog, FetchProgressDialog
import git
from git import GitError
from util import *
from wxutil import *

# Menu item ids
MENU_SWITCH_TO_COMMIT   = 10000
MENU_MERGE_COMMIT       = 10001
MENU_CHERRYPICK_COMMIT  = 10002
MENU_REVERT_COMMIT      = 10003

MENU_CREATE_BRANCH      = 11000
MENU_DELETE_BRANCH      = 12000

# This array is used to provide unique ids for menu items
# that refer to a branch
branch_indexes = []

class HistoryTab(object):
    def __init__(self, mainController):
        self.mainController = mainController
        self.mainWindow = self.mainController.frame
        
        # Commit list
        browserPanel = GetWidget(self.mainWindow, 'historyBrowserPanel')
        browserSizer = browserPanel.GetSizer()
        
        self.commitList = CommitList(browserPanel, -1, False)
        self.commitList.authorColumnPos = self.mainController.config.ReadInt('CommitListAuthorColumnPosition', 200)
        self.commitList.Bind(EVT_COMMITLIST_SELECT, self.OnCommitSelected, self.commitList)
        self.commitList.Bind(EVT_COMMITLIST_RIGHTCLICK, self.OnCommitRightClick, self.commitList)
        browserSizer.Add(self.commitList, 1, wx.EXPAND)
        
        # Diff viewer
        diffPanel = GetWidget(self.mainWindow, "historyDiffPanel")
        diffSizer = diffPanel.GetSizer()
        
        self.diffViewer = DiffViewer(diffPanel, -1)
        diffSizer.Add(self.diffViewer, 1, wx.EXPAND)
        
        # Splitter
        self.splitter = GetWidget(self.mainWindow, "historySplitter")
        self.splitter.SetSashPosition(self.mainController.config.ReadInt('HistorySplitterPosition', 200))

        # Context menu
        self.contextCommit = None
        self.contextMenu = wx.Menu()
        wx.EVT_MENU(self.mainWindow, MENU_SWITCH_TO_COMMIT, self.OnSwitchToCommit)
        wx.EVT_MENU(self.mainWindow, MENU_CREATE_BRANCH, self.OnCreateBranch)
        wx.EVT_MENU(self.mainWindow, MENU_MERGE_COMMIT, self.OnMerge)
        wx.EVT_MENU(self.mainWindow, MENU_CHERRYPICK_COMMIT, self.OnCherryPick)
        wx.EVT_MENU(self.mainWindow, MENU_REVERT_COMMIT, self.OnRevert)
        
        # Other events
        SetupEvents(self.mainWindow, [
            ('fetchTool', wx.EVT_TOOL, self.OnFetch),
            ('switchTool', wx.EVT_TOOL, self.OnSwitchToCommit),
            ('switchMenuItem', wx.EVT_MENU, self.OnSwitchToCommit),
            ('createBranchMenuItem', wx.EVT_MENU, self.OnCreateBranch),
            ('mergeMenuItem', wx.EVT_MENU, self.OnMerge),
            ('cherryPickMenuItem', wx.EVT_MENU, self.OnCherryPick),
            ('revertMenuItem', wx.EVT_MENU, self.OnRevert),
            ('gotoCommitMenuItem', wx.EVT_MENU, self.OnGotoCommit),
        ])

    def SetRepo(self, repo):
        # Branch indexes
        global branch_indexes
        for branch in repo.branches:
            if branch not in branch_indexes:
                branch_indexes.append(branch)

        # Menu events for branches
        for index in xrange(len(branch_indexes)):
            wx.EVT_MENU(self.mainWindow, MENU_DELETE_BRANCH + index, self.OnDeleteBranch)

        self.repo = repo
        self.commitList.SetRepo(repo)

        difftext = self.repo.run_cmd(['show', 'HEAD^'])
        self.diffViewer.Clear()

    def OnCommitSelected(self, e):
        self.contextCommit = self.commitList.CommitByRow(e.currentRow)

        # Show in diff viewer
        commit_diff = self.repo.run_cmd(['show', self.contextCommit.sha1])
        self.diffViewer.SetDiffText(commit_diff, commit_mode=True)

    def OnCommitRightClick(self, e):
        self.contextCommit = self.commitList.CommitByRow(e.currentRow)
        self.SetupContextMenu(self.contextCommit)
        self.commitList.PopupMenu(self.contextMenu, e.coords)

    def OnSwitchToCommit(self, e):
        if not self.contextCommit or self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

        wizard = SwitchWizard(self.mainWindow, -1, self.repo, self.contextCommit)
        result = wizard.RunWizard()

        if result > 0:
            self.mainController.ReloadRepo()

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
        if not self.contextCommit or self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

        dialog = wx.TextEntryDialog(self.mainWindow, "Enter branch name:", "Create branch...")
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
        if not self.contextCommit or self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

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
            self.mainController.ReloadRepo()

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
        if not self.contextCommit or self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

        confirmMsg = "Do you really want to cherry-pick this commit?"
        msg = wx.MessageDialog(
            self.mainWindow,
            confirmMsg,
            "Confirmation",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            retcode, stdout, stderr = self.repo.run_cmd(['cherry-pick', self.contextCommit.sha1], with_retcode=True, with_stderr=True)
            self.mainController.ReloadRepo()

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
        if not self.contextCommit or self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

        confirmMsg = "Do you really want to revert this commit?"
        msg = wx.MessageDialog(
            self.mainWindow,
            confirmMsg,
            "Confirmation",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            retcode, stdout, stderr = self.repo.run_cmd(['revert', self.contextCommit.sha1], with_retcode=True, with_stderr=True)
            self.mainController.ReloadRepo()

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
        setupDialog = FetchSetupDialog(self.mainWindow, -1, self.repo)
        result = setupDialog.ShowModal()

        # Progress dialog
        if result:
            progressDialog = FetchProgressDialog(self.mainWindow, -1, self.repo, setupDialog.selectedRemote, setupDialog.includeSubmodules, setupDialog.fetchTags)
            if progressDialog.ShowModal():
                self.mainController.ReloadRepo()

    def OnFetchProgress(self, eventType, eventParam):
        print 'FETCH CALLBACK:', eventType, eventParam

    def OnGotoCommit(self, e):
        if self.mainController.selectedTab != MainWindow.TAB_HISTORY:
            return

        msg = wx.TextEntryDialog(
            self.mainWindow,
            "Enter commit ID:",
            "Go to Version",
            "",
            wx.ICON_QUESTION | wx.OK | wx.CANCEL
        )
        msg.ShowModal()
        commit_id = msg.GetValue()
        
        if commit_id:
            error = self.commitList.GotoCommit(commit_id)
            if error:
                wx.MessageBox(
                    error,
                    "Error",
                    style=wx.OK|wx.ICON_ERROR
                )

    def SaveState(self):
        self.mainController.config.WriteInt('HistorySplitterPosition', self.splitter.GetSashPosition())
        self.mainController.config.WriteInt('CommitListAuthorColumnPosition', self.commitList.authorColumnPos)

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
        self.contextMenu.Append(MENU_CHERRYPICK_COMMIT, "Apply this commit to HEAD (cherry-pick)")
        self.contextMenu.Append(MENU_REVERT_COMMIT, "Apply the inverse of this commit to HEAD (revert)")

    def GitCommand(self, cmd, check_submodules=False, **opts):
        try:
            retval = self.repo.run_cmd(cmd, raise_error=True, **opts)
            self.mainController.ReloadRepo()

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

