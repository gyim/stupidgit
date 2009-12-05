import wx
from git import *

class FetchSetupDialog(wx.Dialog):
    def __init__(self, parent, id, repo):
        wx.Dialog.__init__(self, parent)
        self.repo = repo

        self.SetTitle('Fetch objects from remote repository')
        self.Bind(wx.EVT_CLOSE, self.OnCancel)

        # Layout
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        remoteSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(remoteSizer, 0, wx.EXPAND | wx.ALL, 5)

        # Remote selector
        remoteChooserText = wx.StaticText(self, -1, 'Remote repository: ')
        remoteSizer.Add(remoteChooserText, 0, wx.ALIGN_CENTRE_VERTICAL, wx.RIGHT, 5)

        self.remoteChoices = [name for name,url in self.repo.remotes.iteritems()]
        self.remoteChoices.sort()

        self.remoteChooser = wx.Choice(self, -1, choices=self.remoteChoices)
        topPadding = 4 if sys.platform == 'darwin' else 0
        remoteSizer.Add(self.remoteChooser, 0, wx.EXPAND | wx.ALIGN_CENTRE_VERTICAL | wx.TOP, topPadding)
        self.remoteChooser.Select(0)
        self.remoteChooser.Bind(wx.EVT_CHOICE, self.OnRemoteChosen)

        # Remote URL
        self.remoteURLText = wx.StaticText(self, -1, '', style=wx.ALIGN_LEFT)
        self.sizer.Add(self.remoteURLText, 0, wx.ALL, 5)

        # Include submodules
        if self.repo.submodules:
            self.submoduleChk = wx.CheckBox(self, -1, label='Also fetch submodule commits')
            self.submoduleChk.SetValue(True)
            self.submoduleChk.Bind(wx.EVT_CHECKBOX, self.OnSubmoduleCheck)
            self.sizer.Add(self.submoduleChk, 0, wx.ALL, 5)
            self.includeSubmodules = True
        else:
            self.includeSubmodules = False

        self.OnRemoteChosen(None)

        # Buttons
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(buttonSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        okButton = wx.Button(self, -1, 'OK')
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        buttonSizer.Add(okButton, 0, wx.RIGHT | wx.BOTTOM, 5)

        cancelButton = wx.Button(self, -1, 'Cancel')
        cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
        buttonSizer.Add(cancelButton, 0, wx.LEFT | wx.BOTTOM, 5)

        self.Fit()

    def OnRemoteChosen(self, e):
        remoteIndex = self.remoteChooser.GetSelection()
        self.selectedRemote = self.remoteChoices[remoteIndex]
        self.remoteURLText.SetLabel('URL: %s' % self.repo.remotes[self.selectedRemote])

        if self.repo.submodules:
            self.submoduleChk.SetLabel('Also fetch submodule commits from remote "%s"' % self.selectedRemote)

        textSize = self.remoteURLText.GetSize()
        winSize = self.GetClientSize()
        self.SetClientSize( (max(winSize[0],textSize[0]+20), winSize[1]) )
        self.Layout()

    def OnSubmoduleCheck(self, e):
        self.includeSubmodules = self.submoduleChk.GetValue()

    def OnOk(self, e):
        self.EndModal(1)

    def OnCancel(self, e):
        self.EndModal(0)

class FetchProgressDialog(wx.Dialog):
    def __init__(self, parent, id, repo, remote, includeSubmodules):
        wx.Dialog.__init__(self, parent, id)
        self.repo = repo
        self.remote = remote
        self.includeSubmodules = includeSubmodules

        # Repositories
        self.repos = [ repo ]
        self.repoIndex = 0
        if includeSubmodules:
            self.repos += [ m for m in repo.submodules if remote in m.remotes ]

        # Layout
        self.SetTitle('Fetching from remote %s...' % remote)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Submodule progress
        if len(self.repos) > 1:
            self.submoduleText = wx.StaticText(self, -1, '')
            self.sizer.Add(self.submoduleText, 0, wx.ALL, 10)

            self.submoduleProgress = wx.Gauge(self, -1)
            self.submoduleProgress.SetRange(len(self.repos)-1)
            self.sizer.Add(self.submoduleProgress, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        else:
            self.submoduleText = None

        # Progress text
        self.progressText = wx.StaticText(self, -1, 'Connecting to remote repository...')
        self.sizer.Add(self.progressText, 0, wx.ALL, 10)

        # Progress bar
        self.progressBar = wx.Gauge(self, -1)
        self.progressBar.SetRange(100)
        self.sizer.Add(self.progressBar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Cancel button
        self.cancelButton = wx.Button(self, -1, 'Cancel')
        self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.sizer.Add(self.cancelButton, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.Bind(wx.EVT_CLOSE, self.OnCancel)

        # Set dialog size
        self.Fit()
        w,h = self.GetClientSize()
        if w < 350:
            self.SetClientSize((350, h))
            self.Layout()

    def ShowModal(self):
        self.StartRepo()
        return wx.Dialog.ShowModal(self)

    def StartRepo(self):
        repo = self.repos[self.repoIndex]

        if self.submoduleText:
            self.submoduleText.SetLabel('Fetching commits for %s...' % repo.name)
            self.submoduleProgress.SetValue(self.repoIndex)

            # Resize window if necessary
            tw,th = self.submoduleText.GetClientSize()
            w,h = self.GetClientSize()
            if w < tw+20:
                self.SetClientSize((tw+20, h))
                self.Layout()

        self.progressText.SetLabel('Connecting to remote repository...')
        self.progressBar.Pulse()
        self.fetchThread = repo.fetch_bg(self.remote, self.ProgressCallback)
        self.repoIndex += 1

    def ProgressCallback(self, event, param):
        if event == FETCH_COUNTING:
            wx.CallAfter(self.progressText.SetLabel, "Counting objects: %d" % param)
        elif event == FETCH_COMPRESSING:
            wx.CallAfter(self.progressText.SetLabel, "Compressing objects...")
            wx.CallAfter(self.progressBar.SetValue, param)
        elif event == FETCH_RECEIVING:
            wx.CallAfter(self.progressText.SetLabel, "Receiving objects...")
            wx.CallAfter(self.progressBar.SetValue, param)
        elif event == FETCH_RESOLVING:
            wx.CallAfter(self.progressText.SetLabel, "Resolving deltas...")
            wx.CallAfter(self.progressBar.SetValue, param)
        elif event == FETCH_ENDED:
            wx.CallAfter(self.OnFetchEnded, param)

    def OnFetchEnded(self, param):
        self.fetchThread.join()
        self.fetchThread = None

        if type(param) in [str, unicode]:
            # Error
            wx.MessageBox(safe_unicode(param), 'Error', style=wx.OK|wx.ICON_ERROR)
            self.EndModal(0)
        else:
            # Success
            if len(self.repos) > self.repoIndex:
                self.StartRepo()
            else:
                self.EndModal(1)

    def OnCancel(self, e):
        if self.fetchThread:
            self.fetchThread.abort()
            self.fetchThread.join()

        self.EndModal(0)

