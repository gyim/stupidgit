import sys
import wx
import git
import platformspec
import os
from Dialogs import CommitListDialog, UncommittedFilesDialog

from util import *

SWMODE_EXISTING_BRANCH  = 'Checkout branch...'
SWMODE_NEW_BRANCH       = 'Checkout as new branch...'
SWMODE_DETACHED_HEAD    = 'Checkout as detached HEAD'
SWMODE_MOVE_BRANCH      = 'Move branch here...'

WORKDIR_CHECKOUT        = 0
WORKDIR_KEEP            = 1

UNCOMMITTED_SAFE_MODE   = 0
UNCOMMITTED_MERGE       = 1
UNCOMMITTED_DISCARD     = 2

SUBMODULE_MOVE_BRANCH   = 0
SUBMODULE_DETACHED_HEAD = 1
SUBMODULE_NEW_BRANCH    = 2

class SwitchWizard(wx.Dialog):
    def __init__(self, parent, id, repo, targetCommit):
        wx.Dialog.__init__(self, parent, id)

        self.repo = repo
        self.targetCommit = targetCommit

        # Basic layout
        self.SetTitle('Switch to version...')
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(sizer, 1, wx.ALL, 5)

        choiceTopPadding = 4 if sys.platform == 'darwin' else 0

        # Detect capabilities
        self.targetBranches = [ branch for (branch,sha1) in self.repo.branches.iteritems() if sha1 == targetCommit.sha1 ]
        self.targetBranches.sort()

        self.allBranches = [ branch for (branch,sha1) in self.repo.branches.iteritems() ]

        if self.targetBranches:
            self.switchModes = [SWMODE_EXISTING_BRANCH, SWMODE_NEW_BRANCH, SWMODE_DETACHED_HEAD, SWMODE_MOVE_BRANCH]
            branchChoices = self.targetBranches
        elif self.allBranches:
            self.switchModes = [SWMODE_NEW_BRANCH, SWMODE_DETACHED_HEAD, SWMODE_MOVE_BRANCH]
            branchChoices = self.allBranches
        else:
            self.switchModes = [SWMODE_NEW_BRANCH, SWMODE_DETACHED_HEAD]
            branchChoices = []

        self.hasUncommittedChanges = (len(self.repo.get_unified_status()) > 0)

        self.hasSubmodules = (len(self.repo.submodules) > 0)

        # Default values
        self.switchMode = self.switchModes[0]
        self.workdirMode = WORKDIR_CHECKOUT
        self.uncommittedMode = UNCOMMITTED_SAFE_MODE
        self.submoduleSwitch = False
        self.submoduleMode = SUBMODULE_MOVE_BRANCH
        self.newBranchName = ''
        self.submoduleBranchName = ''
        if self.switchMode == SWMODE_EXISTING_BRANCH:
            self.targetBranch = self.targetBranches[0]
        else:
            self.targetBranch = ''
        self.error = None
        self.submoduleWarnings = {}

        # -------------------- Switch mode ---------------------
        # Switch mode
        self.swmodeSizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.swmodeSizer, 0, wx.EXPAND | wx.ALL, 5)

        self.swmodeSizer.Add(wx.StaticText(self, -1, 'Switch mode:'), 0, wx.ALIGN_CENTRE_VERTICAL | wx.RIGHT, 5)
        self.swmodeChoices = wx.Choice(self, -1, choices=self.switchModes)
        self.swmodeSizer.Add(self.swmodeChoices, 0, wx.ALIGN_CENTRE_VERTICAL | wx.TOP | wx.RIGHT, choiceTopPadding)
        self.swmodeChoices.Select(0)
        self.Bind(wx.EVT_CHOICE, self.OnSwitchModeChosen, self.swmodeChoices)

        # Branch selector
        self.branchChoices = wx.Choice(self, -1, choices=branchChoices)
        self.swmodeSizer.Add(self.branchChoices, 1, wx.ALIGN_CENTRE_VERTICAL | wx.TOP | wx.RIGHT, choiceTopPadding)
        if branchChoices:
            self.branchChoices.Select(0)
        self.branchChoices.Bind(wx.EVT_CHOICE, self.OnBranchChosen)
        self.branchChoices.Show(self.switchModes[0] != SWMODE_NEW_BRANCH)

        # New branch text box
        self.newBranchTxt = wx.TextCtrl(self, -1)
        self.newBranchTxt.Bind(wx.EVT_TEXT, self.Validate)
        self.swmodeSizer.Add(self.newBranchTxt, 1, wx.ALIGN_CENTRE_VERTICAL | wx.LEFT | wx.RIGHT, 5)
        self.newBranchTxt.Show(self.switchModes[0] == SWMODE_NEW_BRANCH)

        # ------------------ Working directory ------------------
        # Static box
        self.workdirBox = wx.StaticBox(self, -1, 'Working directory:')
        self.workdirSizer = wx.StaticBoxSizer(self.workdirBox, wx.VERTICAL)
        sizer.Add(self.workdirSizer, 0, wx.EXPAND | wx.ALL, 5)

        # Radio buttons
        btn = wx.RadioButton(self, -1, 'Switch file contents to new version', style=wx.RB_GROUP)
        btn.SetValue(True)
        btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnWorkdirMode(WORKDIR_CHECKOUT))
        self.workdirSizer.Add(btn, 0, wx.ALL, 5)

        btn = wx.RadioButton(self, -1, 'Keep files unchanged')
        btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnWorkdirMode(WORKDIR_KEEP))
        self.workdirSizer.Add(btn, 0, wx.ALL, 5)

        # ------------------ Uncommitted changes -----------------
        if self.hasUncommittedChanges:
            self.uncommittedBox = wx.StaticBox(self, -1, 'Uncommitted changes:')
            self.uncommittedSizer = wx.StaticBoxSizer(self.uncommittedBox, wx.VERTICAL)
            sizer.Add(self.uncommittedSizer, 0, wx.EXPAND | wx.ALL, 5)

            # Radio buttons
            self.uncommittedButtons = []

            btn = wx.RadioButton(self, -1, 'Switch only if these files need not to be modified', style=wx.RB_GROUP)
            btn.SetValue(True)
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnUncommittedMode(UNCOMMITTED_SAFE_MODE))
            self.uncommittedButtons.append(btn)
            self.uncommittedSizer.Add(btn, 0, wx.ALL, 5)

            btn = wx.RadioButton(self, -1, 'Merge uncommitted changes into new version')
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnUncommittedMode(UNCOMMITTED_MERGE))
            self.uncommittedButtons.append(btn)
            self.uncommittedSizer.Add(btn, 0, wx.ALL, 5)

            btn = wx.RadioButton(self, -1, 'Discard uncommitted changes')
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnUncommittedMode(UNCOMMITTED_DISCARD))
            self.uncommittedButtons.append(btn)
            self.uncommittedSizer.Add(btn, 0, wx.ALL, 5)

            btn = wx.Button(self, -1, 'Review uncommitted changes')
            btn.Bind(wx.EVT_BUTTON, self.OnReviewUncommittedChanges)
            self.uncommittedSizer.Add(btn, 0, wx.ALL, 5)

        # ----------------------- Submodules ----------------------
        if self.hasSubmodules:
            self.submoduleBox = wx.StaticBox(self, -1, 'Submodules:')
            self.submoduleSizer = wx.StaticBoxSizer(self.submoduleBox, wx.VERTICAL)
            sizer.Add(self.submoduleSizer, 0, wx.EXPAND | wx.ALL, 5)

            # Submodule checkbox
            self.submoduleChk = wx.CheckBox(self, -1, 'Switch submodules to referenced version')
            self.submoduleChk.SetValue(False)
            self.submoduleChk.Bind(wx.EVT_CHECKBOX, self.OnSubmoduleSwitch)
            self.submoduleSizer.Add(self.submoduleChk, 0, wx.ALL, 5)

            # Radio buttons
            self.submoduleModeButtons = []

            btn = wx.RadioButton(self, -1, 'Move currently selected branches (only if no commits will be lost)', style=wx.RB_GROUP)
            btn.SetValue(1)
            btn.Enable(False)
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnSubmoduleMode(SUBMODULE_MOVE_BRANCH))
            self.submoduleSizer.Add(btn, 0, wx.ALL, 5)
            self.submoduleModeButtons.append(btn)

            btn = wx.RadioButton(self, -1, 'Switch to detached HEAD')
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnSubmoduleMode(SUBMODULE_DETACHED_HEAD))
            btn.Enable(False)
            self.submoduleSizer.Add(btn, 0, wx.ALL, 5)
            self.submoduleModeButtons.append(btn)

            s = wx.BoxSizer(wx.HORIZONTAL)
            self.submoduleSizer.Add(s, 0, wx.ALL, 5)

            btn = wx.RadioButton(self, -1, 'Switch to new branch:')
            btn.Bind(wx.EVT_RADIOBUTTON, lambda e:self.OnSubmoduleMode(SUBMODULE_NEW_BRANCH))
            btn.Enable(False)
            s.Add(btn, 0)
            self.submoduleModeButtons.append(btn)

            # New branch text field
            self.submoduleBranchTxt = wx.TextCtrl(self, -1)
            self.submoduleBranchTxt.Bind(wx.EVT_TEXT, self.Validate)
            s.Add(self.submoduleBranchTxt, 0, wx.LEFT, 7)
            self.submoduleBranchTxt.Enable(False)

        # Status message
        self.statusSizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.statusSizer, 0, wx.EXPAND | wx.TOP, 15)

        self.statusMsg = wx.StaticText(self, -1, '')
        self.statusSizer.Add(self.statusMsg, 1, wx.LEFT, 5)

        self.statusButton = wx.Button(self, -1, 'Details')
        self.statusButton.Bind(wx.EVT_BUTTON, self.OnDetailsButton)
        self.statusSizer.Add(self.statusButton, 0, wx.LEFT | wx.RIGHT, 5)

        # Finish buttons
        s = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(s, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_RIGHT, 15)

        self.okButton = wx.Button(self, -1, 'OK')
        self.okButton.Bind(wx.EVT_BUTTON, self.OnOkClicked)
        s.Add(self.okButton, 0, wx.LEFT | wx.RIGHT, 5)

        self.cancelButton = wx.Button(self, -1, 'Cancel')
        self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancelClicked)
        s.Add(self.cancelButton, 0, wx.LEFT | wx.RIGHT, 5)

        self.Validate()

        # Resize window
        self.Fit()
        self.Layout()
        w,h = self.GetSize()
        self.SetSize((max(450,w),h))

    def Validate(self, e=None):
        isValid = True

        # If we are on a detached head, we may always lose commits
        self.lostCommits = []
        if not self.repo.current_branch:
            self.lostCommits = self.repo.get_lost_commits('HEAD', self.targetCommit.sha1)

        # Validate branch name
        if self.switchMode == SWMODE_NEW_BRANCH:
            self.newBranchName = self.newBranchTxt.GetValue().strip()
            if not self.newBranchName:
                isValid = False
                self.statusMsg.SetLabel('Enter the name of the new branch!')
            elif self.newBranchName in self.repo.branches.keys():
                isValid = False
                self.statusMsg.SetLabel("Branch '%s' already exists!" % self.newBranchName)

        # Check lost commits of moved branch
        elif self.switchMode == SWMODE_MOVE_BRANCH:
            lostCommits = self.repo.get_lost_commits('refs/heads/' + self.targetBranch, self.targetCommit.sha1)
            for c in lostCommits:
                if c not in self.lostCommits:
                    self.lostCommits.append(c)

        # Check submodule branch name
        if isValid and self.submoduleMode == SUBMODULE_NEW_BRANCH:
            self.submoduleBranchName = self.submoduleBranchTxt.GetValue().strip()
            if not self.submoduleBranchName:
                isValid = False
                self.statusMsg.SetLabel('Enter the name of the new submodule branch!')

        # Enable / disable controls according to validity
        if isValid:
            self.okButton.Enable(1)

            # Show warning about lost commits
            if self.lostCommits:
                if len(self.lostCommits) == 1:
                    msg = 'WARNING: You will permanently lose a commit!'
                else:
                    msg = 'WARNING: You will permanently lose %d commits!' % len(self.lostCommits)
                self.statusMsg.SetLabel(msg)
                self.statusButton.Show(1)
            else:
                self.statusMsg.SetLabel('')
                self.statusButton.Show(0)
        else:
            self.okButton.Enable(0)
            self.statusButton.Show(0)

        # Refresh layout
        self.statusSizer.Layout()

    def OnSwitchModeChosen(self, e):
        self.switchMode = e.GetString()

        if self.switchMode == SWMODE_EXISTING_BRANCH:
            self.branchChoices.Show(1)
            self.newBranchTxt.Show(0)

            self.targetBranch = self.targetBranches[0]
            self.branchChoices.Clear()
            for branch in self.targetBranches:
                self.branchChoices.Append(branch)
            self.branchChoices.Select(0)

        elif self.switchMode == SWMODE_NEW_BRANCH:
            self.branchChoices.Show(0)
            self.newBranchTxt.Show(1)

            self.newBranchTxt.SetValue('')

        elif self.switchMode == SWMODE_DETACHED_HEAD:
            self.branchChoices.Show(0)
            self.newBranchTxt.Show(0)

        elif self.switchMode == SWMODE_MOVE_BRANCH:
            self.branchChoices.Show(1)
            self.newBranchTxt.Show(0)

            self.targetBranch = self.allBranches[0]
            self.branchChoices.Clear()
            for branch in self.allBranches:
                self.branchChoices.Append(branch)
            self.branchChoices.Select(0)

        self.swmodeSizer.RecalcSizes()
        self.Validate()

    def OnBranchChosen(self, e):
        if self.switchMode in [SWMODE_EXISTING_BRANCH, SWMODE_MOVE_BRANCH]:
            self.targetBranch = e.GetString()
        else:
            self.targetBranch = ''

        self.Validate()

    def OnWorkdirMode(self, workdirMode):
        self.workdirMode = workdirMode

        if self.hasUncommittedChanges:
            uncommittedModeEnabled = (workdirMode == WORKDIR_CHECKOUT)
            for btn in self.uncommittedButtons:
                btn.Enable(uncommittedModeEnabled)

        self.Validate()

    def OnUncommittedMode(self, uncommittedMode):
        self.uncommittedMode = uncommittedMode
        self.Validate()

    def OnReviewUncommittedChanges(self, e):
        dialog = UncommittedFilesDialog(self, -1, self.repo)
        dialog.SetTitle('Uncommitted changes')
        dialog.SetMessage('The following changes are not committed:')
        dialog.ShowModal()

    def OnDetailsButton(self, e):
        if self.repo.current_branch == None:
            if self.switchMode == SWMODE_MOVE_BRANCH:
                message = 'By moving a detached HEAD and/or branch \'%s\' to a different position ' % self.targetBranch
            else:
                message = 'By moving a detached HEAD to a different position '
        else:
            message = 'By moving branch \'%s\' to a different position ' % self.targetBranch

        message += 'some of the commits will not be referenced by any ' + \
                   'branch, tag or remote branch. They will disappear from the ' + \
                   'history graph and will be permanently lost.\n\n' + \
                   'These commits are:'

        dialog = CommitListDialog(self, -1, self.repo, self.lostCommits)
        dialog.SetTitle('Review commits to be lost')
        dialog.SetMessage(message)
        dialog.ShowModal()

    def OnSubmoduleSwitch(self, e):
        self.submoduleSwitch = self.submoduleChk.GetValue()

        for btn in self.submoduleModeButtons:
            btn.Enable(self.submoduleSwitch)

        if self.submoduleSwitch:
            self.submoduleBranchTxt.Enable(self.submoduleMode == SUBMODULE_NEW_BRANCH)
        else:
            self.submoduleBranchTxt.Enable(False)

        self.Validate()

    def OnSubmoduleMode(self, submoduleMode):
        self.submoduleMode = submoduleMode
        self.submoduleBranchTxt.Enable(submoduleMode == SUBMODULE_NEW_BRANCH)
        self.Validate()

    def OnOkClicked(self, e):
        # Update references
        self.repo.load_refs()

        try:
            # Switch to new version (as detached HEAD)
            if self.workdirMode == WORKDIR_KEEP:
                self.repo.run_cmd(['update-ref', '--no-deref', 'HEAD', self.targetCommit.sha1], raise_error=True)
            elif self.uncommittedMode == UNCOMMITTED_SAFE_MODE:
                self.repo.run_cmd(['checkout', self.targetCommit.sha1], raise_error=True)
            elif self.uncommittedMode == UNCOMMITTED_MERGE:
                self.repo.run_cmd(['checkout', '-m', self.targetCommit.sha1], raise_error=True)
            elif self.uncommittedMode == UNCOMMITTED_DISCARD:
                self.repo.run_cmd(['reset', '--hard', self.targetCommit.sha1], raise_error=True)
                self.repo.run_cmd(['clean', '-f'], raise_error=True)

            # Checkout branch
            branch = None
            if self.switchMode in [SWMODE_EXISTING_BRANCH, SWMODE_MOVE_BRANCH]:
                branch = self.targetBranch
            elif self.switchMode == SWMODE_NEW_BRANCH:
                branch = self.newBranchName
            if branch:
                if self.switchMode != SWMODE_EXISTING_BRANCH:
                    self.repo.run_cmd(['update-ref', 'refs/heads/%s' % branch, self.targetCommit.sha1], raise_error=True)
                self.repo.update_head('ref: refs/heads/%s' % branch)

        except git.GitError, e:
            self.error = str(e).partition('\n')[2].strip()
            if not self.error:
                self.error = str(e)
            self.EndModal(1)
            return

        # Update submodules
        if self.submoduleSwitch:
            self.repo.load_refs()

            for submodule in self.repo.submodules:
                submodule.load_refs()
                submodule.get_log(['--topo-order', '--all']) # Update commit pool

                # Check existence of referenced commit
                if submodule.main_ref not in git.commit_pool:
                    self.submoduleWarnings[submodule.name] = 'Referenced version cannot be found'
                    continue
                commit = git.commit_pool[submodule.main_ref]
                
                # Check lost commits
                lostCommits = submodule.get_lost_commits('HEAD', commit.sha1)
                if self.submoduleMode == SUBMODULE_MOVE_BRANCH and submodule.current_branch:
                    lostCommits += submodule.get_lost_commits('refs/heads/%s' % submodule.current_branch, commit.sha1)
                if lostCommits:
                    self.submoduleWarnings[submodule.name] = 'Switching to new version would result in lost commits'
                    continue

                # Try to checkout (in safe mode)
                try:
                    # Reset submodule so that it won't be unmerged
                    self.repo.run_cmd(['reset', submodule.name])

                    if self.submoduleMode == SUBMODULE_DETACHED_HEAD:
                        submodule.run_cmd(['checkout', commit.sha1], raise_error=True)
                    elif self.submoduleMode == SUBMODULE_NEW_BRANCH:
                        if self.submoduleBranchName in submodule.branches:
                            self.submoduleWarnings[submodule.name] = "Branch '%s' already exists!" % self.submoduleBranchName
                            continue
                        submodule.run_cmd(['branch', self.submoduleBranchName, commit.sha1], raise_error=True)
                        submodule.run_cmd(['checkout', self.submoduleBranchName], raise_error=True)
                    elif self.submoduleMode == SUBMODULE_MOVE_BRANCH:
                        submodule.run_cmd(['checkout', commit.sha1], raise_error=True)
                        if submodule.current_branch:
                            submodule.run_cmd(['update-ref', 'refs/heads/%s' % submodule.current_branch, commit.sha1], raise_error=True)
                            submodule.run_cmd(['checkout', submodule.current_branch], raise_error=True)
                except git.GitError, e:
                    error_line = str(e).partition('\n')[2].strip()
                    if not error_line:
                        error_line = e
                    self.submoduleWarnings[submodule.name] = error_line

        self.EndModal(1)

    def OnCancelClicked(self, e):
        self.EndModal(0)

    def RunWizard(self):
        return self.ShowModal()

