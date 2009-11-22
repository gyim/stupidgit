# -*- coding: utf-8
from git import *
from HistoryTab import HistoryTab
from IndexTab import IndexTab
import wx

STUPIDGIT_VERSION = "v0.1.1"

ID_NEWWINDOW    = 101
ID_CLOSEWINDOW  = 102

app_windows = []
license_text = u'''
Copyright (c) 2009 Ákos Gyimesi

Permission is hereby granted, free of charge, to
any person obtaining a copy of this software and
associated documentation files (the "Software"),
to deal in the Software without restriction,
including without limitation the rights to use,
copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is
furnished to do so, subject to the following
conditions:

The above copyright notice and this permission
notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY
OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT.  IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF
OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
'''

class MainWindow(wx.Frame):
    def __init__(self, parent, id, repo):
        # Read default window size
        self.config = wx.Config('stupidgit')
        width  = self.config.ReadInt('MainWindowWidth', 550)
        height = self.config.ReadInt('MainWindowHeight', 600)

        # Create window
        wx.Frame.__init__(self, parent, wx.ID_ANY, "stupidgit", size=(width,height))
        app_windows.append(self)

        self.CreateMenu()
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Load repository or static text
        if repo:
            self.emptyText = None
            self.SetMainRepo(repo)
        else:
            self.mainRepo = None
            self.currentRepo = None
            self.CreateEmptyText()

    def CreateMenu(self):
        filemenu = wx.Menu()
        filemenu.Append(ID_NEWWINDOW, "&New window\tCtrl-N", "Open new window")
        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_OPEN)
        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_EXIT)

        windowmenu = wx.Menu()
        windowmenu.Append(ID_CLOSEWINDOW, "Close &Window\tCtrl-W")

        helpmenu = wx.Menu()
        helpmenu.Append(wx.ID_ABOUT, "&About", "About stupidgit")

        menubar = wx.MenuBar()
        menubar.Append(filemenu, "&File")
        menubar.Append(windowmenu, "&Window")
        menubar.Append(helpmenu, "&Help")
        self.SetMenuBar(menubar)

        wx.EVT_MENU(self, ID_NEWWINDOW, self.OnNewWindow)
        wx.EVT_MENU(self, ID_CLOSEWINDOW, lambda e: self.Close(True))
        wx.EVT_MENU(self, wx.ID_OPEN, self.OnOpenRepository)
        wx.EVT_MENU(self, wx.ID_EXIT, self.OnExit)
        wx.EVT_MENU(self, wx.ID_ABOUT, self.OnAbout)

    def OnNewWindow(self, e):
        win = MainWindow(None, -1, None)
        win.Show(True)

    def OnOpenRepository(self, e):
        repodir = wx.DirSelector("Open repository")
        if not repodir: return

        try:
            repo = Repository(repodir)

            if self.mainRepo:
                new_win = MainWindow(None, -1, repo)
                new_win.Show(True)
            else:
                self.SetMainRepo(repo)
        except GitError, msg:
            wx.MessageBox(str(msg), 'Error', style=wx.OK|wx.ICON_ERROR)

    def OnAbout(self, e):
        info = wx.AboutDialogInfo()
        info.SetName("stupidgit")
        info.SetDescription("A cross-platform git GUI with strong submodule support.\n\nHomepage: http://github.com/gyim/stupidgit")
        info.SetVersion(STUPIDGIT_VERSION)
        info.SetCopyright(u"(c) Ákos Gyimesi, 2009.")
        info.SetLicense(license_text)

        wx.AboutBox(info)

    def OnClose(self, e):
        # Save window geometry
        size = self.GetSize()
        self.config.WriteInt('MainWindowWidth', size.GetWidth())
        self.config.WriteInt('MainWindowHeight', size.GetHeight())

        # Close window
        app_windows.remove(self)
        self.Destroy()

    def OnExit(self, e):
        while app_windows:
            app_windows[0].Close(True)

    def CreateRepoControls(self):
        if self.emptyText:
            self.emptyText.Destroy()

        # Top panel
        self.topPanel = wx.Panel(self, -1)
        self.sizer.Add(self.topPanel, 0, wx.EXPAND)
        topSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.topPanel.SetSizer(topSizer)

        self.moduleLbl = wx.StaticText(self.topPanel, -1, 'Module:')
        topSizer.Add(self.moduleLbl, 0, wx.ALIGN_CENTRE_VERTICAL | wx.ALL, 5)

        # Module chooser
        module_choices = [s.name for s in self.mainRepo.all_modules]
        self.moduleChooser = wx.Choice(self.topPanel, -1, choices=module_choices)
        topPadding = 4 if sys.platform == 'darwin' else 0
        topSizer.Add(self.moduleChooser, 1, wx.ALIGN_CENTRE_VERTICAL | wx.TOP, topPadding)
        self.moduleChooser.Select(0)
        self.Bind(wx.EVT_CHOICE, self.OnModuleChosen, self.moduleChooser)

        self.refreshBtn = wx.Button(self.topPanel, -1, 'Refresh')
        topSizer.Add(self.refreshBtn, 0, wx.ALIGN_CENTRE_VERTICAL | wx.LEFT | wx.RIGHT, 5)
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, self.refreshBtn)

        # Notebook
        self.pageChooser = wx.Notebook(self, -1)
        self.sizer.Add(self.pageChooser, 1, wx.EXPAND)

        # History page
        self.historyTab = HistoryTab(self, self.pageChooser, -1)
        self.pageChooser.AddPage(self.historyTab, "History")

        # Index tab
        self.indexTab = IndexTab(self, self.pageChooser, -1)
        self.pageChooser.AddPage(self.indexTab, "Index")

        self.pageChooser.ChangeSelection(0)

        self.SetRepo(self.mainRepo)
        self.sizer.Layout()

    def CreateEmptyText(self):
        self.emptyText = wx.StaticText(self, -1, 'Welcome to stupidgit!\n\nYou can open a repository in the File menu.')
        self.sizer.Add(self.emptyText, 1, wx.EXPAND | wx.ALL, 10)

    def SetMainRepo(self, repo):
        self.mainRepo = repo
        self.currentRepo = repo

        if repo:
            title = "stupidgit - %s" % os.path.basename(repo.dir)
        else:
            title = "stupidgit"

        self.SetTitle(title)
        self.CreateRepoControls()

    def SetRepo(self, repo):
        self.currentRepo = repo
        self.currentRepo.load_refs()
        self.historyTab.SetRepo(repo)
        self.indexTab.SetRepo(repo)

    def ReloadRepo(self):
        self.currentRepo.load_refs()
        self.SetRepo(self.currentRepo)

        # Load referenced version in submodules
        for submodule in self.currentRepo.submodules:
            submodule.load_refs()

    def OnModuleChosen(self, e):
        module_name = e.GetString()
        module = [m for m in self.mainRepo.all_modules if m.name == module_name]
        if module:
            self.SetRepo(module[0])

    def OnRefresh(self, e):
        self.currentRepo.load_refs()
        self.SetRepo(self.currentRepo)

