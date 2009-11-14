from git import *
from HistoryTab import HistoryTab
from IndexTab import IndexTab
import wx

ID_NEWWINDOW = 101
ID_OPEN      = 102
ID_EXIT      = 103

class MainWindow(wx.Frame):
    def __init__(self, parent, id, repo):
        wx.Frame.__init__(self, parent, wx.ID_ANY, "stupidgit", size=(550,600))

        self.CreateMenu()

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        if repo:
            self.emptyText = None
            self.SetMainRepo(repo)
        else:
            self.mainRepo = None
            self.currentRepo = None
            self.CreateEmptyText()

    def CreateMenu(self):
        filemenu = wx.Menu()
        filemenu.Append(ID_NEWWINDOW, "&New window", "Open new window")
        filemenu.AppendSeparator()
        filemenu.Append(ID_OPEN, "&Open repository", "Open an existing repository")
        filemenu.AppendSeparator()
        filemenu.Append(ID_EXIT, "E&xit", "Exit stupidgit")

        menubar = wx.MenuBar()
        menubar.Append(filemenu, "&File")
        self.SetMenuBar(menubar)

        wx.EVT_MENU(self, ID_NEWWINDOW, self.OnNewWindow)
        wx.EVT_MENU(self, ID_OPEN, self.OnOpenRepository)
        wx.EVT_MENU(self, ID_EXIT, self.OnExit)

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

    def OnExit(self, e):
        self.Close(True)

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

