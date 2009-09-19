import locale

def safe_unicode(s):
    '''Creates unicode object from string s.
    It tries to decode string as UTF-8, fallbacks to current locale
    or ISO-8859-1 if both decode attemps fail'''

    if type(s) == unicode:
        return s
    
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

