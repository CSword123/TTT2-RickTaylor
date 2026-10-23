"""Rick's files for his own roster slot (recomp/runtime/rick_slot.cpp, TTT2_RICK=1), for ttt2rick.ttt2.overlay.

python -m ttt2rick.convert.slot <game folder> <converted Rick (ttt2rick.convert.rick's out dir)> <out dir>

Writes <out>/files: ric.nud/.nut/.bon/.xml (the converted body files, renamed), key_52494331.bin (Marduk's moveset with
Rick's id in its header) and ric/alo/... (copies of Marduk's effect files and their textures: the title loads a
fighter's effects as <code>/alo/<name>.alo, with its own code).
"""
import os
import struct
import sys

from ..ttt2.archive import Archives
from ..ttt2.petexy import itemdb

CODE, DONOR = 'ric', 'mar'
ID, DONOR_ID, DONOR_ROW = 64, 17, 17
MOVESET_KEY = 0x52494331                  # rick_slot.cpp kMovesetKey
MOTION_ROWS = 0x820A24B4                  # in the game image (game/tekken.img, loaded at 0x82000000)
IMAGE_BASE = 0x82000000
ALO_END = b'AL_EFFECT\0'


def moveset(arc, image):
    key = struct.unpack_from('>I', image, MOTION_ROWS - IMAGE_BASE + 12 * DONOR_ROW)[0]
    ms = bytearray(arc.read(key))
    ids = struct.unpack_from('>4h', ms, 0xF8 + 64)
    if ids != (DONOR_ID - 1, -(DONOR_ID - 1), DONOR_ID, -DONOR_ID):
        raise ValueError('motion row %d is not Marduk\'s moveset (ids %s)' % (DONOR_ROW, ids))
    struct.pack_into('>4h', ms, 0xF8 + 64, ID - 1, -(ID - 1), ID, -ID)
    return bytes(ms)


def effects(arc):
    """{path under the overlay: bytes}: Marduk's effect files and their textures under Rick's code."""
    out = {}
    names = itemdb.effect_names(arc.read_name(DONOR + '.xml'))
    for name in names:
        src = '%s/alo/%s.alo' % (DONOR, name)
        if not arc.has(arc_key(src)):
            continue
        data = arc.read_name(src)
        out['%s/alo/%s.alo' % (CODE, name)] = data
        at = data.find(ALO_END)
        for t in (data[at + len(ALO_END):].split(b'\0') if at >= 0 else []):
            if t.endswith(b'.nut'):
                tex = '%s/alo/texture/%s' % (DONOR, t.decode('latin1'))
                if arc.has(arc_key(tex)):
                    out['%s/alo/texture/%s' % (CODE, t.decode('latin1'))] = arc.read_name(tex)
    return out, names


def arc_key(name):
    from ..ttt2.archive import key_of
    return key_of(name)


def main(game, rick, out):
    arc = Archives(game)
    folder = game if os.path.isdir(os.path.join(game, 'game')) is False else os.path.join(game, 'game')
    image = open(os.path.join(folder, 'tekken.img'), 'rb').read()
    files = {}
    for ext in ('nud', 'nut', 'bon', 'xml'):
        files['%s.%s' % (CODE, ext)] = open(os.path.join(rick, 'files', '%s.%s' % (DONOR, ext)), 'rb').read()
    files['key_%08x.bin' % MOVESET_KEY] = moveset(arc, image)
    fx, names = effects(arc)
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
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
