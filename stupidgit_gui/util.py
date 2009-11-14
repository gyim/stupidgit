import locale
import sys
import os
import os.path
import subprocess

def safe_unicode(s):
    '''Creates unicode object from string s.
    It tries to decode string as UTF-8, fallbacks to current locale
    or ISO-8859-1 if both decode attemps fail'''

    if type(s) == unicode:
        return s
    elif isinstance(s, Exception):
        s = str(s)
    
    try:
        return s.decode('UTF-8')
    except UnicodeDecodeError:
        pass

    lang,encoding = locale.getdefaultlocale()

    if encoding != 'UTF-8':
        try:
            return s.decode(encoding)
        except UnicodeDecodeError:
            pass

    return s.decode('ISO-8859-1')

def utf8_str(s):
    s = safe_unicode(s)
    return s.encode('UTF-8')

def invert_hash(h):
    ih = {}

    for key,value in h.iteritems():
        if value not in ih:
            ih[value] = []
        ih[value].append(key)

    return ih

def find_binary(locations):
    searchpath_sep = ';' if sys.platform == 'win32' else ':'
    searchpaths = os.environ['PATH'].split(searchpath_sep)

    for location in locations:
        if '{PATH}' in location:
            for searchpath in searchpaths:
                s = location.replace('{PATH}', searchpath)
                if os.path.isfile(s) and os.access(s, os.X_OK):
                    yield s
        elif os.path.isfile(location) and os.access(location, os.X_OK):
            yield location

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

CREATE_NO_WINDOW = 0x08000000
def Popen(cmd, **args):
    if sys.platform == 'win32':
        return subprocess.Popen(cmd, creationflags = CREATE_NO_WINDOW, **args)
    else:
        return subprocess.Popen(cmd, **args)

