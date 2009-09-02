from git import *
from OverviewTab import OverviewTab
from HistoryTab import HistoryTab
from IndexTab import IndexTab
import wx

ID_NEWWINDOW = 101
ID_NEW       = 102
ID_OPEN      = 103
ID_EXIT      = 104

class MainWindow(wx.Frame):
    def __init__(self, parent, id, title, repo):
        wx.Frame.__init__(self, parent, wx.ID_ANY, title, size=(550,600))
        self.mainRepo = repo
        self.currentRepo = repo
        
        self.CreateMenu()

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        if repo:
            self.emptyText = None
            self.CreateRepoControls()
        else:
            self.CreateEmptyText()

    def CreateMenu(self):
        filemenu = wx.Menu()
        filemenu.Append(ID_NEWWINDOW, "&New window", "Open new window")
        filemenu.AppendSeparator()
        filemenu.Append(ID_NEW, "&New repository", "Create a new repository")
        filemenu.Append(ID_OPEN, "&Open repository", "Open an existing repository")
        filemenu.AppendSeparator()
        filemenu.Append(ID_EXIT, "E&xit", "Exit stupidgit")

        menubar = wx.MenuBar()
        menubar.Append(filemenu, "&File")
        self.SetMenuBar(menubar)

        wx.EVT_MENU(self, ID_NEWWINDOW, self.OnNewWindow)
        wx.EVT_MENU(self, ID_NEW, self.OnNewRepository)
        wx.EVT_MENU(self, ID_OPEN, self.OnOpenRepository)
        wx.EVT_MENU(self, ID_EXIT, self.OnExit)

    def OnNewWindow(self, e):
        win = MainWindow(None, -1, "stupidgit", None)
        win.Show(True)

    def OnNewRepository(self, e):
        pass

    def OnOpenRepository(self, e):
        repodir = wx.DirSelector("Open repository")
        if not repodir: return

        try:
            self.mainRepo = Repository(repodir)
            self.CreateRepoControls()
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

        self.manageBtn = wx.Button(self.topPanel, -1, 'Manage modules')
        topSizer.Add(self.manageBtn, 0, wx.ALIGN_CENTRE_VERTICAL | wx.LEFT | wx.RIGHT, 5)

        self.refreshBtn = wx.Button(self.topPanel, -1, 'Refresh')
        topSizer.Add(self.refreshBtn, 0, wx.ALIGN_CENTRE_VERTICAL | wx.RIGHT, 5)
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, self.refreshBtn)

        # Notebook
        self.pageChooser = wx.Notebook(self, -1)
        self.sizer.Add(self.pageChooser, 1, wx.EXPAND)

        # Overview page
        self.overviewTab = OverviewTab(self, self.pageChooser, -1)
        self.pageChooser.AddPage(self.overviewTab, "Overview")

        # History page
        self.historyTab = HistoryTab(self, self.pageChooser, -1)
        self.pageChooser.AddPage(self.historyTab, "History")

        # Index tab
        self.indexTab = IndexTab(self, self.pageChooser, -1)
        self.pageChooser.AddPage(self.indexTab, "Index")

        self.pageChooser.ChangeSelection(1)

        self.SetRepo(self.mainRepo)
        self.sizer.Layout()

    def CreateEmptyText(self):
        self.emptyText = wx.StaticText(self, -1, 'Welcome to stupidgit!\n\nYou can create or open a repository in the File menu.')
        self.sizer.Add(self.emptyText, 1, wx.EXPAND)

    def SetRepo(self, repo):
        self.currentRepo = repo
        self.currentRepo.load_refs()
        self.overviewTab.SetRepo(repo)
        self.historyTab.SetRepo(repo)
        self.indexTab.SetRepo(repo)

    def OnModuleChosen(self, e):
        module_name = e.GetString()
        module = [m for m in self.mainRepo.all_modules if m.name == module_name]
        if module:
            self.SetRepo(module[0])

    def OnRefresh(self, e):
        self.currentRepo.load_refs()
        self.SetRepo(self.currentRepo)

