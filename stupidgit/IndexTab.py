# -*- encoding: utf-8

import wx
import wx.html
import os
import sys

import Wizard
from DiffViewer import DiffViewer
from git import GitError
from util import *

FILE_ADDED       = 'A'
FILE_MODIFIED    = 'M'
FILE_DELETED     = 'D'
FILE_COPIED      = 'C'
FILE_RENAMED     = 'R'
FILE_UNMERGED    = 'U'
FILE_TYPECHANGED = 'T'
FILE_UNTRACKED   = 'N'
FILE_BROKEN      = 'B'
FILE_UNKNOWN     = 'X'

MOD_DESCS = {
    FILE_ADDED       : 'added',
    FILE_MODIFIED    : 'modified',
    FILE_DELETED     : 'deleted',
    FILE_COPIED      : 'copied',
    FILE_RENAMED     : 'renamed',
    FILE_UNMERGED    : 'unmerged',
    FILE_TYPECHANGED : 'type changed',
    FILE_UNTRACKED   : 'untracked',
    FILE_BROKEN      : 'BROKEN',
    FILE_UNKNOWN     : 'UNKNOWN'
}

if sys.platform in ['win32', 'cygwin']:
    LABEL_STAGE = u"Stage >"
    LABEL_UNSTAGE = u"< Unstage"
    LABEL_DISCARD = u"× Discard"
else:
    LABEL_STAGE = u"Stage ⇒"
    LABEL_UNSTAGE = u"⇐ Unstage"
    LABEL_DISCARD = u"× Discard"

class IndexTab(wx.Panel):
    def __init__(self, mainWindow, parent, id):
        wx.Panel.__init__(self, parent, id)
        self.mainWindow = mainWindow
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # --- File lists ---
        self.listRow = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.listRow, 0, wx.EXPAND)

        # Unstaged changes
        self.unstagedBox = wx.StaticBox(self, -1, "Unstaged changes")
        self.unstagedBoxSizer = wx.StaticBoxSizer(self.unstagedBox, wx.VERTICAL)
        self.listRow.Add(self.unstagedBoxSizer, 1, wx.EXPAND | wx.RIGHT, 10)

        self.unstagedList = wx.ListBox(self, -1, style=wx.LB_EXTENDED)
        self.unstagedBoxSizer.Add(self.unstagedList, 1, wx.EXPAND|wx.ALL, 0)
        self.Bind(wx.EVT_LISTBOX, self.OnUnstagedListSelect, self.unstagedList)

        # Stage/unstage/discard buttons
        self.actionButtons = wx.BoxSizer(wx.VERTICAL)
        self.listRow.Add(self.actionButtons, 0, wx.BOTTOM, 5)

        self.stageButton = wx.Button(self, -1, LABEL_STAGE)
        self.unstageButton = wx.Button(self, -1, LABEL_UNSTAGE)
        self.discardButton = wx.Button(self, -1, LABEL_DISCARD)

        self.Bind(wx.EVT_BUTTON, self.OnStage, self.stageButton)
        self.Bind(wx.EVT_BUTTON, self.OnUnstage, self.unstageButton)
        self.Bind(wx.EVT_BUTTON, self.OnDiscard, self.discardButton)

        self.actionButtons.Add(self.stageButton, 0, wx.EXPAND | wx.TOP, 20)
        self.actionButtons.Add(self.unstageButton, 0, wx.EXPAND | wx.TOP, 5)
        self.actionButtons.Add(self.discardButton, 0, wx.EXPAND | wx.TOP, 20)

        # Staged changes
        self.stagedBox = wx.StaticBox(self, -1, "Staged changes")
        self.stagedBoxSizer = wx.StaticBoxSizer(self.stagedBox, wx.VERTICAL)
        self.listRow.Add(self.stagedBoxSizer, 1, wx.EXPAND | wx.LEFT, 10)

        self.stagedList = wx.ListBox(self, -1, style=wx.LB_EXTENDED)
        self.stagedBoxSizer.Add(self.stagedList, 1, wx.EXPAND|wx.ALL, 0)
        self.Bind(wx.EVT_LISTBOX, self.OnStagedListSelect, self.stagedList)

        # Diff viewer
        self.diffViewer = DiffViewer(self, -1)
        self.sizer.Add(self.diffViewer, 2, wx.EXPAND)

        # Commit / discard buttons
        self.bottomButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.bottomButtons, 0, wx.TOP | wx.BOTTOM, 5)

        self.commitButton = wx.Button(self, -1, "Commit staged changes")
        self.resetButton = wx.Button(self, -1, "Discard all changes")

        self.Bind(wx.EVT_BUTTON, self.OnCommit, self.commitButton)
        self.Bind(wx.EVT_BUTTON, self.OnReset, self.resetButton)

        self.bottomButtons.Add(self.commitButton, 0, wx.LEFT, 5)
        self.bottomButtons.Add(self.resetButton, 0, wx.LEFT, 5)

    def OnStage(self, e):
        for row in self.unstagedList.GetSelections():
            filename = self.unstagedChanges[row][0]
            self.repo.run_cmd(['add', filename])

        self.Refresh()

    def OnUnstage(self, e):
        for row in self.stagedList.GetSelections():
            filename = self.stagedChanges[row][0]
            self.repo.run_cmd(['reset', 'HEAD', filename])

        self.Refresh()

    def OnDiscard(self, e):
        # Get selection
        rows = self.unstagedList.GetSelections()
        if len(rows) == 0:
            return

        # Confirm dialog
        msg = wx.MessageDialog(
            self.mainWindow,
            "The selected changes will be permanently lost. Do you really want to continue?",
            "Warning",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            for row in rows:
                filename = self.unstagedChanges[row][0]
                if filename in self.untrackedFiles:
                    try: os.unlink(os.path.join(self.repo.dir, filename))
                    except OSError: pass
                else:
                    self.repo.run_cmd(['checkout', filename])

        self.Refresh()

    def OnUnstagedListSelect(self, e):
        # Clear selection in stagedList
        for row in self.stagedList.GetSelections():
            self.stagedList.Deselect(row)

        # Show diffs
        selection = list(self.unstagedList.GetSelections())
        selection.sort()

        diff_text = ''
        for row in selection:
            filename = self.unstagedChanges[row][0]
            if filename in self.untrackedFiles:
                # Start "diff" text
                if diff_text:
                    diff_text += '\n'
                diff_text += 'New file: %s\n' % filename

                # Detect whether file is binary
                if is_binary_file(filename):
                    diff_text += "@@ File is binary.\n\n"
                else:
                    # Text file => show lines
                    newfile_text = ''
                    try:
                        f = open(filename, 'r')
                        lines = f.readlines()
                        f.close()

                        newfile_text += '@@ -1,0 +1,%d @@\n' % len(lines)

                        for line in lines:
                            newfile_text += '+ ' + line

                        diff_text += newfile_text
                    except OSError:
                        diff_text += '@@ Error: Cannot open file\n\n'

            else:
                diff_text += self.repo.run_cmd(['diff', self.unstagedChanges[row][0]])

        self.diffViewer.SetDiffText(diff_text)

    def OnStagedListSelect(self, e):
        # Clear selection in unstagedList
        for row in self.unstagedList.GetSelections():
            self.unstagedList.Deselect(row)

        # Show diffs
        selection = list(self.stagedList.GetSelections())
        selection.sort()

        diff_text = ''
        for row in selection:
            diff_text += self.repo.run_cmd(['diff', '--cached', self.stagedChanges[row][0]])

        self.diffViewer.SetDiffText(diff_text)

    def OnCommit(self, e):
        if len(self.stagedChanges) == 0:
            return

        # Show commit wizard
        commit_wizard = CommitWizard(self.mainWindow, -1, self.repo)
        commit_wizard.RunWizard()
        self.Refresh()

    def OnReset(self, e):
        msg = wx.MessageDialog(
            self.mainWindow,
            "This operation will discard ALL (both staged and unstaged) changes. Do you really want to continue?",
            "Warning",
            wx.ICON_EXCLAMATION | wx.YES_NO | wx.YES_DEFAULT
        )
        if msg.ShowModal() == wx.ID_YES:
            self.repo.run_cmd(['reset', '--hard'])
            self.repo.run_cmd(['clean', '-f'])

            self.Refresh()

    def SetRepo(self, repo):
        self.repo = repo

        # Unstaged changes
        self.unstagedChanges = self._parse_diff_output(['diff-files', '-z'])
        self.untrackedFiles = self.repo.run_cmd(['ls-files', '--others', '--exclude-standard', '-z']).split('\x00')
        for f in self.untrackedFiles:
            if f: self.unstagedChanges.append((f, FILE_UNTRACKED))

        self.unstagedList.Clear()
        self.unstagedList.InsertItems( ['%s (%s)' % (c[0], MOD_DESCS[c[1]]) for c in self.unstagedChanges], 0 )

        # Staged changes
        self.stagedChanges = self._parse_diff_output(['diff-index', '--cached', '-z', 'HEAD'])

        self.stagedList.Clear()
        self.stagedList.InsertItems( ['%s (%s)' % (c[0], MOD_DESCS[c[1]]) for c in self.stagedChanges], 0 )

    def Refresh(self):
        self.SetRepo(self.repo)

    def _parse_diff_output(self, cmd):
        output = self.repo.run_cmd(cmd)
        result = []

        items = output.split('\x00')
        for i in xrange(len(items)/2):
            mod, filename = items[2*i], items[2*i+1]
            old_mode, new_mode, old_sha1, new_sha1, mod_type = mod.split(' ')
            result.append((filename, mod_type[0]))

        return result

def is_binary_file(file):
    # Returns True if the file cannot be decoded as UTF-8
    # and > 20% of the file is binary character

    # Read file
    try:
        f = open(file)
        buf = f.read()
        f.close()
    except OSError:
        return False

    # Decode as UTF-8
    try:
        ubuf = unicode(buf, 'utf-8')
        return False
    except UnicodeDecodeError:
        pass

    # Check number of binary characters
    treshold = len(buf) / 5
    binary_chars = 0
    for c in buf:
        oc = ord(c)
        if oc > 0x7f or (oc < 0x1f and oc != '\r' and oc != '\n'):
            binary_chars += 1
            if binary_chars > treshold:
                return True

    return False

class CommitWizard(Wizard.Wizard):
    def __init__(self, parent, id, repo):
        Wizard.Wizard.__init__(self, parent, id)
        self.repo = repo

        # --- Modified submodules warning page ---
        self.submoduleWarningPage = self.CreateWarningPage(
            "Warning",

            "There are uncommitted changes in one or more submodules.\n\n" +
            "If you want these changes to be saved in this version, " +
            "commit the submodules first, then stage the new submodule versions " +
            "to the main module.\n\n" +
            "Do you still want to continue?",

            [Wizard.BTN_CANCEL, Wizard.BTN_CONTINUE]
        )

        # --- Commit page ---
        self.commitPage = self.CreatePage("Commit staged changes")
        s = self.commitPage.sizer

        # Author
        s.Add(wx.StaticText(self.commitPage, -1, "Author:"), 0, wx.TOP, 5)

        authorSizer = wx.BoxSizer(wx.HORIZONTAL)
        s.Add(authorSizer, 0, wx.EXPAND)

        self.authorEntry = wx.TextCtrl(self.commitPage, -1, style=wx.TE_READONLY)
        self.authorEntry.Disable()
        authorSizer.Add(self.authorEntry, 1, wx.ALL, 5)

        self.changeAuthorBtn = wx.Button(self.commitPage, -1, 'Change')
        authorSizer.Add(self.changeAuthorBtn, 0, wx.ALL, 5)
        
        # Short message
        s.Add(wx.StaticText(self.commitPage, -1, "Commit description:"), 0, wx.TOP, 5)
        self.shortmsgEntry = wx.TextCtrl(self.commitPage, -1)
        s.Add(self.shortmsgEntry, 0, wx.EXPAND | wx.ALL, 5)

        # Details
        s.Add(wx.StaticText(self.commitPage, -1, "Commit details:"), 0, wx.TOP, 5)
        self.detailsEntry = wx.TextCtrl(self.commitPage, -1, style=wx.TE_MULTILINE)
        s.Add(self.detailsEntry, 1, wx.EXPAND | wx.ALL, 5)

        # Amend
        self.amendChk = wx.CheckBox(self.commitPage, -1, "Amend (add to previous commit)")
        s.Add(self.amendChk, 0, wx.EXPAND | wx.ALL, 5)

    def OnStart(self):
        # Check whether submodules have changes
        self.hasSubmoduleChanges = False
        for module in self.repo.submodules:
            diffs = module.run_cmd(['diff', 'HEAD'])
            new_files = module.run_cmd(['ls-files', '--others', '--exclude-standard'])
            if len(diffs.strip()) > 0 or len(new_files.strip()) > 0:
                self.hasSubmoduleChanges = True
                break

        # Get author info
        self.authorName  = self.repo.run_cmd(['config', 'user.name']).strip()
        self.authorEmail = self.repo.run_cmd(['config', 'user.email']).strip()
        self.authorEntry.SetValue(u"%s <%s>" % (safe_unicode(self.authorName), safe_unicode(self.authorEmail)))

        # Show first page
        if self.hasSubmoduleChanges:
            self.commitPage.buttons = [Wizard.BTN_PREV, Wizard.BTN_FINISH]
            self.SetPage(self.submoduleWarningPage)
        else:
            self.commitPage.buttons = [Wizard.BTN_CANCEL, Wizard.BTN_FINISH]
            self.SetPage(self.commitPage)

    def OnButtonClicked(self, button):
        if button == Wizard.BTN_CANCEL:
            self.EndWizard(0)
        
        # Submodule warning page
        if self.currentPage == self.submoduleWarningPage:
            self.SetPage(self.commitPage)

        # Commit page
        elif self.currentPage == self.commitPage:
            if button == Wizard.BTN_PREV:
                self.SetPage(self.submoduleWarningPage)
            elif button == Wizard.BTN_FINISH:
                if self.Validate():
                    # Commit changes
                    short_msg = self.shortmsgEntry.GetValue()
                    details = self.detailsEntry.GetValue()
                    is_amend = self.amendChk.GetValue()

                    if len(details.strip()):
                        msg = "%s\n\n%s" % (short_msg, details)
                    else:
                        msg = short_msg

                    try:
                        self.repo.commit(self.authorName, self.authorEmail, msg, amend=is_amend)
                    except GitError, msg:
                        msg = wx.MessageDialog(
                            self,
                            msg,
                            "Git error",
                            wx.ICON_ERROR | wx.OK
                        )
                        
                    self.EndWizard(0)
                else:
                    # Show alert
                    if len(self.authorName) == 0 or len(self.authorEmail) == 0:
                        errormsg = "Please set author name!"
                    else:
                        errormsg = "Please fill in commit description!"

                    msg = wx.MessageDialog(
                        self,
                        errormsg,
                        "Notice",
                        wx.ICON_EXCLAMATION | wx.OK
                    )
                    msg.ShowModal()

    def Validate(self):
        return len(self.authorName) != 0 and len(self.authorEmail) != 0 and \
            len(self.shortmsgEntry.GetValue()) != 0

