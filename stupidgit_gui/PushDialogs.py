import wx
from wxutil import *
from util import *
from git import *

class PushSetupDialog(object):
    def __init__(self, parent, id, repo):
        self.dialog = LoadDialog(parent, 'PushDialog')
        self.dialog.SetMinSize((400, -1))
        self.repo = repo
        
        # Widgets
        self.remoteChooser = GetWidget(self.dialog, 'remoteChooser')
        self.branchChooser = GetWidget(self.dialog, 'branchChooser')
        self.branchEntry = GetWidget(self.dialog, 'branchEntry')
        self.warningLabel = GetWidget(self.dialog, 'warningLabel')
        self.detailsButton = GetWidget(self.dialog, 'detailsButton')
        self.forcePushCheckbox = GetWidget(self.dialog, 'forcePushCheckbox')
        
        # Events
        SetupEvents(self.dialog, [
            ('remoteChooser', wx.EVT_CHOICE, self.OnRemoteChosen),
            ('branchChooser', wx.EVT_CHOICE, self.OnBranchChosen),
            ('branchEntry', wx.EVT_TEXT, self.OnBranchText),
            ('forcePushCheckbox', wx.EVT_CHECKBOX, self.OnForcePush)
        ])
        
        # Setup remotes
        self.remoteChoices = [name for name,url in self.repo.remotes.iteritems()]
        self.remoteChoices.sort()
        
        self.remoteChooser = GetWidget(self.dialog, 'remoteChooser')
        for remote in self.remoteChoices:
            self.remoteChooser.Append(remote)
        self.remoteChooser.Select(0)
        self.OnRemoteChosen()
        
        # Setup initial settings
        self.forcePush = False
        self.HideWarning()

    def ShowModal(self):
        self.dialog.Fit()
        return self.dialog.ShowModal()

    def OnRemoteChosen(self, e=None):
        remoteIndex = self.remoteChooser.GetSelection()
        self.selectedRemote = self.remoteChoices[remoteIndex]
        
        # Update branches
        prefix = '%s/' % self.selectedRemote
        self.remoteBranches = [b[len(prefix):] for b in self.repo.remote_branches.keys() if b.startswith(prefix)]
        self.remoteBranches.sort()
        
        self.branchChooser.Clear()
        for branch in self.remoteBranches:
            self.branchChooser.Append(branch)
        self.branchChooser.Append('New branch...')
        self.branchChooser.Select(0)
        self.OnBranchChosen()

    def OnBranchChosen(self, e=None):
        branchIndex = self.branchChooser.GetSelection()
        if branchIndex == len(self.remoteBranches):
            self.branchEntry.Show()
            self.selectedBranch = self.branchEntry.GetValue()
        else:
            self.branchEntry.Hide()
            self.selectedBranch = self.remoteBranches[branchIndex]

        self.dialog.Layout()
        self.dialog.Fit()
    
    def OnBranchText(self, e):
        self.selectedBranch = self.branchEntry.GetValue()
    
    def OnForcePush(self, e):
        self.forcePush = self.forcePushCheckbox.GetValue()
    
    def HideWarning(self):
        self.warningLabel.Hide()
        self.detailsButton.Hide()

class PushProgressDialog(object):
    def __init__(self, parent, id, repo, remote, commit, remoteBranch, forcePush):
        self.parent = parent
        self.repo = repo
        self.remote = remote
        self.commit = commit
        self.remoteBranch = remoteBranch
        self.forcePush = forcePush
        
        # Setup dialog
        self.dialog = LoadDialog(parent, 'PushProgressDialog')
        self.dialog.SetMinSize((350, -1))
        self.dialog.SetTitle('Pushing to %s...' % remote)
        
        # Widgets
        self.progressLabel = GetWidget(self.dialog, 'progressLabel')
        self.progressBar = GetWidget(self.dialog, 'progressBar')
        SetupEvents(self.dialog, [
            ('cancelButton', wx.EVT_BUTTON, self.OnCancel)
        ])
    
    def ShowModal(self):
        self.progressLabel.SetLabel('Connecting to remote repository...')
        self.progressBar.Pulse()
        self.dialog.Fit()
        
        self.pushThread = self.repo.push_bg(self.remote, self.commit, self.remoteBranch, self.forcePush, self.ProgressCallback)
        return self.dialog.ShowModal()
    
    def ProgressCallback(self, event, param):
        if event == TRANSFER_COMPRESSING:
            wx.CallAfter(self.progressLabel.SetLabel, "Compressing objects...")
            wx.CallAfter(self.progressBar.SetValue, param)
        elif event == TRANSFER_WRITING:
            wx.CallAfter(self.progressLabel.SetLabel, "Writing objects...")
            wx.CallAfter(self.progressBar.SetValue, param)
        elif event == TRANSFER_ENDED:
            wx.CallAfter(self.OnPushEnded, param)
    
    def OnPushEnded(self, error):
        if error:
            wx.MessageBox(safe_unicode(error), 'Error', style=wx.OK|wx.ICON_ERROR)
            self.dialog.EndModal(0)
        else:
            self.dialog.EndModal(1)
    
    def OnCancel(self, e):
        self.pushThread.abort()
        self.dialog.EndModal(0)
