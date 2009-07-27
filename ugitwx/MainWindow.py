from git import *
import wx

ID_NEWWINDOW = 101
ID_NEW       = 102
ID_OPEN      = 103
ID_EXIT      = 104

class MainWindow(wx.Frame):
    def __init__(self, parent, id, title, repo):
        wx.Frame.__init__(self, parent, wx.ID_ANY, title, size=(550,600))
        self.repo = repo
        
        self.CreateMenu()
        self.panel = None

        if repo:
            self.CreateRepoPanel()
        else:
            self.CreateEmptyPanel()

    def CreateMenu(self):
        filemenu = wx.Menu()
        filemenu.Append(ID_NEWWINDOW, "&New window", "Open new window")
        filemenu.AppendSeparator()
        filemenu.Append(ID_NEW, "&New repository", "Create a new repository")
        filemenu.Append(ID_OPEN, "&Open repository", "Open an existing repository")
        filemenu.AppendSeparator()
        filemenu.Append(ID_EXIT, "E&xit", "Exit ugitwx")

        menubar = wx.MenuBar()
        menubar.Append(filemenu, "&File")
        self.SetMenuBar(menubar)

        wx.EVT_MENU(self, ID_NEWWINDOW, self.OnNewWindow)
        wx.EVT_MENU(self, ID_NEW, self.OnNewRepository)
        wx.EVT_MENU(self, ID_OPEN, self.OnOpenRepository)
        wx.EVT_MENU(self, ID_EXIT, self.OnExit)

    def OnNewWindow(self, e):
        win = MainWindow(None, -1, "ugitwx", None)
        win.Show(True)

    def OnNewRepository(self, e):
        pass

    def OnOpenRepository(self, e):
        repodir = wx.DirSelector("Open repository")
        if not repodir: return

        try:
            self.repo = Repository(repodir)
            self.CreateRepoPanel()
        except GitError, msg:
            wx.MessageBox(str(msg), 'Error', style=wx.OK|wx.ICON_ERROR)

    def OnExit(self, e):
        self.Close(True)

    def CreateRepoPanel(self):
        if self.panel:
            self.panel.Destroy()

    def CreateEmptyPanel(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel = wx.StaticText(self, -1, 'Welcome to ugitwx!\n\nYou can create or open a repository in the File menu.')
        sizer.Add(self.panel, 1, wx.EXPAND, wx.ALL)

