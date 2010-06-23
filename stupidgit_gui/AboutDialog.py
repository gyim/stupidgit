# -*- coding: utf-8
import wx

STUPIDGIT_VERSION = "v0.1.1"

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

def ShowAboutDialog():
    info = wx.AboutDialogInfo()
    info.SetName("stupidgit")
    info.SetDescription("A cross-platform git GUI with strong submodule support.\n\nHomepage: http://github.com/gyim/stupidgit")
    info.SetVersion(STUPIDGIT_VERSION)
    info.SetCopyright(u"(c) Ákos Gyimesi, 2009.")
    info.SetLicense(license_text)

    wx.AboutBox(info)
