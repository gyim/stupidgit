import sys
import os
import wx

platform = None
default_font = None

# Init non-GUI specific parts
def init():
    global platform

    if not platform:
        # Determine platform name
        if sys.platform in ['win32', 'cygwin']:
            platform = 'win'
        elif sys.platform == 'darwin':
            platform = 'osx'
        elif os.name == 'posix':
            platform = 'unix' # I know, OSX is unix, too :)
        else:
            platform = 'other'

# Init platform-specific values
def init_wx():
    global default_font
        
    # Fonts
    default_font = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)

# Font creator that solves the headache with pixel sizes
# - in most cases...
def Font(size, family=None, style=wx.FONTSTYLE_NORMAL, weight=wx.FONTWEIGHT_NORMAL):
    init_wx()

    if not family:
        family = default_font.GetFamily()
    
    font = wx.Font(size, family, style, weight)
    if platform == 'win':
        font.SetPixelSize((size*2,size))

    return font

# Initialize module
init()

