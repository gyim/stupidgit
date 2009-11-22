import wx
import wx.stc
import platformspec
from util import *

STYLE_NORMAL  = 1
STYLE_COMMIT  = 2
STYLE_FILE    = 3
STYLE_HUNK    = 4
STYLE_ADD     = 5
STYLE_REMOVE  = 6

MARK_FILE = 1

STYLE_COLORS = [
    None,
    ('#000000', '#FFFFFF', wx.FONTWEIGHT_NORMAL), # STYLE_NORMAL
    ('#000000', '#FFFFFF', wx.FONTWEIGHT_BOLD),   # STYLE_COMMIT
    ('#000000', '#AAAAAA', wx.FONTWEIGHT_BOLD),   # STYLE_FILE
    ('#0000AA', '#FFFFFF', wx.FONTWEIGHT_NORMAL), # STYLE_HUNK
    ('#008800', '#FFFFFF', wx.FONTWEIGHT_NORMAL), # STYLE_ADD
    ('#AA0000', '#FFFFFF', wx.FONTWEIGHT_NORMAL)  # STYLE_REMOVE
]

class DiffViewer(wx.Panel):
    def __init__(self, parent, id):
        wx.Panel.__init__(self, parent, id)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Create text control
        self.textCtrl = wx.stc.StyledTextCtrl(self, -1)
        self.sizer.Add(self.textCtrl, 1, wx.EXPAND)

        # Create markers
        self.textCtrl.MarkerDefine(MARK_FILE,
            wx.stc.STC_MARK_BACKGROUND,
            wx.Colour(0,0,0,255),
            wx.Colour(192,192,192,255)
        )

        # Create text styles
        for style in xrange(1, len(STYLE_COLORS)):
            fg, bg, weight = STYLE_COLORS[style]
            font = platformspec.Font(10, wx.FONTFAMILY_TELETYPE)
            
            self.textCtrl.StyleSetFont(style, font)
            self.textCtrl.StyleSetForeground(style, fg)
            self.textCtrl.StyleSetBackground(style, bg)

    def Clear(self):
        self.textCtrl.SetReadOnly(False)
        self.textCtrl.SetText('')
        self.textCtrl.SetReadOnly(True)

    def SetDiffText(self, text, commit_mode=False):
        self.Clear()
        self.textCtrl.SetReadOnly(False)

        # Setup commit mode (when the text comes from the
        # output of git show, not git diff)
        if commit_mode:
            in_commit_header = True
            in_commit_msg = False
        else:
            in_commit_header = False
            in_commit_msg = False

        in_hunk = False
        style = STYLE_NORMAL
        pos = 0
        lineno = 0
        for line in text.split('\n'):
            # Determine line style
            if in_commit_header:
                if line == '':
                    in_commit_header = False
                    in_commit_msg = True
                style = STYLE_COMMIT
            elif in_commit_msg:
                if line == '':
                    in_commit_msg = False
                style = STYLE_COMMIT
            elif in_hunk:
                if line.startswith('+'):
                    style = STYLE_ADD
                elif line.startswith('-'):
                    style = STYLE_REMOVE
                elif line.startswith('@'):
                    style = STYLE_HUNK
                elif line.startswith(' '):
                    style = STYLE_NORMAL
                else:
                    in_hunk = False
                    style = STYLE_FILE
            else:
                if line.startswith('@'):
                    style = STYLE_HUNK
                    in_hunk = True
                else:
                    style = STYLE_FILE

            # Add line
            self.textCtrl.AddText(safe_unicode(line) + '\n')
            self.textCtrl.StartStyling(pos, 0xff)
            self.textCtrl.SetStyling(len(line), style)
            pos += len(line) + 1

            if style == STYLE_FILE and len(line) > 0:
                self.textCtrl.MarkerAdd(lineno, MARK_FILE)

            lineno += 1

        self.textCtrl.SetReadOnly(True)
            
