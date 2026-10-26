"""Jennifer's files for her own roster slot (recomp/runtime/rick_slot.cpp, TTT2_JEN=1), for ttt2rick.ttt2.overlay.

python -m ttt2jen.slot <game folder> <her body (ttt2jen.convert's out, with ttt2jen.motions' pack)> <Rick's slot
                       (ttt2rick.convert.slot's out)> <out dir>

Writes <out>/files: jen.nud/.nut/.bon/.xml (her body), key_4a454e32.bin ("JEN2", her motion pack: Rick's with her feet
planted), key_4a454e31.bin ("JEN1": Rick's moveset, his attacks and guard, with her id 65 in its header) and
jen/alo/... (Nina's effect files and their textures under her code, as her item database is Nina's). Her pictures
(portraits, HUD, layouts) are made with Rick's (ttt2rick.convert.portrait, hud, layouts: the containers they share),
so they come with Rick's slot files: install both, Rick's first.
"""
import os
import struct
import sys

from ttt2rick.convert import slot as rick_slot
from ttt2rick.ttt2.archive import Archives

from .convert import CODE, DONOR
from .motions import JEN_MOTIONS

ID = 65                                    # rick_slot.cpp: Jennifer's id
MOVESET_KEY = 0x4A454E31                   # "JEN1": rick_slot.cpp's
RICK_ID = rick_slot.ID


def moveset(rick):
    ms = bytearray(rick)
    ids = struct.unpack_from('>4h', ms, 0xF8 + 64)
    if ids != (RICK_ID - 1, -(RICK_ID - 1), RICK_ID, -RICK_ID):
        raise ValueError('not Rick\'s moveset (ids %s)' % (ids,))
    struct.pack_into('>4h', ms, 0xF8 + 64, ID - 1, -(ID - 1), ID, -ID)
    return bytes(ms)


def main(game, body, rick, out):
    arc = Archives(game)
    files = {}
    for ext in ('nud', 'nut', 'bon', 'xml'):
        files['%s.%s' % (CODE, ext)] = open(os.path.join(body, 'files', '%s.%s' % (CODE, ext)), 'rb').read()
    files['key_%08x.bin' % JEN_MOTIONS] = open(os.path.join(body, 'files', 'key_%08x.bin' % JEN_MOTIONS), 'rb').read()
    files['key_%08x.bin' % MOVESET_KEY] = moveset(
        open(os.path.join(rick, 'files', 'key_%08x.bin' % rick_slot.MOVESET_KEY), 'rb').read())
    fx, names = rick_slot.effects(arc, DONOR, CODE)
    files.update(fx)
    dest = os.path.join(out, 'files')
    for root, dirs, fs in os.walk(dest, topdown=False):
        for f in fs:
            os.remove(os.path.join(root, f))
        for d in dirs:
            os.rmdir(os.path.join(root, d))
    for path, data in files.items():
        p = os.path.join(dest, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(data)
    print('%s: %d files (%d effect files of %d names)' % (dest, len(files), len(fx), len(names)))


if __name__ == '__main__':
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
