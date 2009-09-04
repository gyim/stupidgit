import wx

BTN_NEXT     = "Next >"
BTN_PREV     = "< Previous"
BTN_CONTINUE = "Continue >"
BTN_CANCEL   = "Cancel"
BTN_FINISH   = "Finish"

class Wizard(wx.Dialog):
    def __init__(self, parent, id):
        wx.Dialog.__init__(self, parent, id, size=wx.Size(600,400))

        # Layout
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Page container
        self.pageSizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.pageSizer, 1, wx.EXPAND | wx.ALL, 5)
        self.currentPage = None

        # Button container
        self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.buttonSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.buttons = []

    def SetPage(self, page):
        # Remove old page from layout
        if self.currentPage:
            self.pageSizer.Detach(self.currentPage)
            self.currentPage.Hide()

        # Add new page to layout
        self.currentPage = page
        self.currentPage.Show()
        self.pageSizer.Add(self.currentPage, 1, wx.EXPAND)
        self.currentPage.sizer.Layout()
        self.pageSizer.Layout()
        self.sizer.Layout()
        
        # Show buttons
        self.SetButtons(page.buttons)

        # Replace title
        self.SetTitle(page.caption)

    def SetButtons(self, buttonLabels):
        for button in self.buttons:
            self.buttonSizer.Detach(button)
            button.Destroy()

        self.buttons = [ wx.Button(self, -1, label) for label in buttonLabels ]
        for button in self.buttons:
            self.Bind(wx.EVT_BUTTON, self._onButton, button)
            self.buttonSizer.Add(button, 0, wx.LEFT, 5)

        self.sizer.Layout()

    def _onButton(self, e):
        self.OnButtonClicked(e.GetEventObject().GetLabel())

    def RunWizard(self):
        self.OnStart()
        self.ShowModal()

    def EndWizard(self, retval):
        self.EndModal(retval)

    # Abstract functions
    def OnStart(self):
        pass

    def OnButtonClicked(self, button):
        pass

    # Helper functions to create pages
    def CreatePage(self, caption, buttons=[]):
        page = wx.Panel(self, -1)
        page.caption = caption
        page.buttons = buttons
        page.sizer = wx.BoxSizer(wx.VERTICAL)
        page.SetSizer(page.sizer)
        page.Hide()

        return page

    def CreateWarningPage(self, caption, message, buttons=[]):
        page = self.CreatePage(caption, buttons)

        captionFont = wx.Font(16, wx.DEFAULT, wx.NORMAL, wx.BOLD) 
        page.captionText = wx.StaticText(page, -1, caption)
        page.captionText.SetFont(captionFont)

        page.text = wx.StaticText(page, -1, message)

        page.sizer.Add(page.captionText, 0, wx.ALL, 10)
        page.sizer.Add(page.text, 1, wx.EXPAND | wx.ALL, 10)
        
        return page

