import wx

class PasswordDialog(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id)
        self.SetTitle('SSH authentication')

        if not title:
            title = 'Password:'
        self.password = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        txt = wx.StaticText(self, -1, title)
        sizer.Add(txt, 1, wx.EXPAND | wx.ALL, 10)

        self.passwordEntry = wx.TextCtrl(self, -1, style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)
        self.passwordEntry.Bind(wx.EVT_TEXT_ENTER, self.OnOk)
        sizer.Add(self.passwordEntry, 0, wx.EXPAND | wx.ALL, 10)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btnSizer, 0, wx.EXPAND | wx.ALL, 10)

        btnOk = wx.Button(self, -1, 'OK')
        btnOk.Bind(wx.EVT_BUTTON, self.OnOk)
        btnSizer.Add(btnOk, 0, wx.EXPAND | wx.RIGHT, 5)

        btnCancel = wx.Button(self, -1, 'Cancel')
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        btnSizer.Add(btnCancel, 0, wx.EXPAND | wx.LEFT, 5)

        self.Fit()

    def OnOk(self, e):
        self.password = self.passwordEntry.GetValue()
        self.EndModal(1)

    def OnCancel(self, e):
        self.EndModal(0)

