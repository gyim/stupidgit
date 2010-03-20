import os
import os.path
import wx
from wx import xrc

_resource_dir = None
def resource_dir():
    global _resource_dir
    if 'STUPIDGIT_RESOURCES' in os.environ:
        _resource_dir = os.environ['STUPIDGIT_RESOURCES']
    elif not _resource_dir:
        _resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources'))

    return _resource_dir

_xrc_resource = None
def _xrc():
    global _xrc_resource
    if not _xrc_resource:
        print os.path.join(resource_dir(), 'stupidgit.xrc')
        _xrc_resource = xrc.XmlResource(os.path.join(resource_dir(), 'stupidgit.xrc'))

    return _xrc_resource

def LoadFrame(parent, frameName):
    return _xrc().LoadFrame(parent, frameName)

def LoadDialog(parent, frameName):
    return _xrc().LoadDialog(parent, frameName)

def SetupEvents(parent, eventHandlers):
    for name, event, handler in eventHandlers:
        if name:
            parent.Bind(event, handler, id=xrc.XRCID(name))
        else:
            parent.Bind(event, handler)

def GetWidget(parent, name):
    return xrc.XRCCTRL(parent, name)

