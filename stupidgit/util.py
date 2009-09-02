import locale

def safe_unicode(s):
    '''Creates unicode object from string s.
    It tries to decode string as UTF-8, fallbacks to current locale
    or ISO-8859-1 if both decode attemps fail'''
    
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
