"""TTT2 format readers/writers and conversion helpers from Petexy's Wii U port (MIT, see LICENSE).

Source: github.com/Petexy/Tekken-Tag-2-Ultimate-Edition @ 581c048, tools/characters/ttt2char:
ttt2/nud.py, ttt2/nut.py, ttt2/bone.py, ttt2/bxml.py, bc.py, convert/skeleton.py, convert/strips.py and
convert/itemdb.py; ttt2/lmb.py (unchanged) and parts of convert/art.py (art.py, its own docstring says what). Changes: imports made local to this package (`from . import ...`), and bxml.py's string encoding is
a module constant ENCODING set to 'cp932' (the Xbox 360 item databases are Shift-JIS; the Wii U's are UTF-8).
They take the Wii U magics (NDP3, NTP3); ttt2rick.ttt2.xbox adapts them to the Xbox 360 files.
"""
