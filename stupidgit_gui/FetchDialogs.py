import wx
from git import *

class FetchSetupDialog(wx.Dialog):
    def __init__(self, parent, id, repo):
        wx.Dialog.__init__(self, parent, id, size=(350, 150))
        self.repo = repo

        self.SetTitle('Fetch objects from remote repository')

        # Layout
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        remoteSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(remoteSizer, 0, wx.EXPAND | wx.ALL, 10)

        # Remote selector
        remoteChooserText = wx.StaticText(self, -1, 'Remote repository: ')
        remoteSizer.Add(remoteChooserText, 0, wx.ALIGN_CENTRE_VERTICAL, wx.RIGHT, 5)

        self.remoteChoices = [name for name,url in self.repo.remotes.iteritems()]
        self.remoteChoices.sort()

        self.remoteChooser = wx.Choice(self, -1, choices=self.remoteChoices)
        topPadding = 4 if sys.platform == 'darwin' else 0
        remoteSizer.Add(self.remoteChooser, 1, wx.EXPAND | wx.ALIGN_CENTRE_VERTICAL | wx.TOP, topPadding)
        self.remoteChooser.Select(0)
        self.remoteChooser.Bind(wx.EVT_CHOICE, self.OnRemoteChosen)

        # Remote URL
        self.remoteURLText = wx.StaticText(self, -1, '', style=wx.ALIGN_LEFT)
        self.sizer.Add(self.remoteURLText, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        self.OnRemoteChosen(None)

        # Buttons
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(buttonSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        okButton = wx.Button(self, -1, 'OK')
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        buttonSizer.Add(okButton, 0, wx.RIGHT, 5)

        cancelButton = wx.Button(self, -1, 'Cancel')
        cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
        buttonSizer.Add(cancelButton, 0, wx.LEFT, 5)

    def OnRemoteChosen(self, e):
        remoteIndex = self.remoteChooser.GetSelection()
        self.selectedRemote = self.remoteChoices[remoteIndex]
        self.remoteURLText.SetLabel('URL: %s' % self.repo.remotes[self.selectedRemote])
        self.sizer.Layout()

    def OnOk(self, e):
        self.EndModal(1)

    def OnCancel(self, e):
        self.EndModal(0)

class FetchProgressDialog(wx.Dialog):
    def __init__(self, parent, id, repo, remote):
        wx.Dialog.__init__(self, parent, id)
        self.repo = repo
        self.remote = remote

        # Layout
        self.SetTitle('Fetching from remote %s...' % remote)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Progress text
        self.progressText = wx.StaticText(self, -1, 'Connecting to remote repository...')
        self.sizer.Add(self.progressText, 0, wx.EXPAND | wx.ALL, 10)

        # Progress bar
        self.progressBar = wx.Gauge(self, -1)
        self.progressBar.SetRange(100)
        self.sizer.Add(self.progressBar, 0, wx.EXPAND | wx.ALL, 10)

        # Cancel button
        self.cancelButton = wx.Button(self, -1, 'Cancel')
        self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.sizer.Add(self.cancelButton, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.Bind(wx.EVT_CLOSE, self.OnCancel)
        self.Fit()

    def ShowModal(self):
        self.progressBar.Pulse()
        self.fetchThread = self.repo.fetch_bg(self.remote, self.ProgressCallback)
        return wx.Dialog.ShowModal(self)

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
            self.EndModal(1)

    def OnCancel(self, e):
        if self.fetchThread:
            self.fetchThread.abort()
            self.fetchThread.join()

        self.EndModal(0)

