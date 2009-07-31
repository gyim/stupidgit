import wx
import wx.html

class OverviewTab(wx.Panel):
    def __init__(self, mainWindow, parent, id):
        wx.Panel.__init__(self, parent, id)
        self.mainWindow = mainWindow

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.text = wx.html.HtmlWindow(self, -1)
        self.text.SetPage('''
        This will be an <b>overview</b> of the repository
        ''')
        self.sizer.Add(self.text, True, wx.EXPAND)

        self.SetSizer(self.sizer)

    def SetRepo(self, repo):
        pass
