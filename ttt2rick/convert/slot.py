"""Rick's files for his own roster slot (recomp/runtime/rick_slot.cpp, TTT2_RICK=1), for ttt2rick.ttt2.overlay.

python -m ttt2rick.convert.slot <game folder> <converted Rick (ttt2rick.convert.rick's out dir)> <out dir> [art dir]

Writes <out>/files: ric.nud/.nut/.bon/.xml and ric_blood.nut (the converted body files, renamed; the bloody NUT for
TTT2_RICK_BLOOD=1), key_52494331.bin (Marduk's moveset with Rick's id in its header, his guard: the standing
guards, sGrd_* moves playing the common Bco_gurd_* animations, play his own, ttt2rick.convert.idle GUARD_ANIM; and
his attacks' moves, ttt2rick.convert.attacks edit_moveset) and ric/alo/... (copies of Marduk's effect files and
their textures: the title loads a fighter's effects as <code>/alo/<name>.alo, with its own code); with an art dir
(ttt2rick.convert.portrait's out), also its files/ (Rick's portraits).
"""
import os
import struct
import sys

from ..ttt2.archive import Archives
from ..ttt2.petexy import itemdb, motbin
from . import attacks, menus
from .idle import GUARD_ANIM

CODE, DONOR = 'ric', 'mar'
ID, DONOR_ID, DONOR_ROW = 64, 17, 17
MOVESET_KEY = 0x52494331                  # rick_slot.cpp kMovesetKey
MOTION_ROWS = 0x820A24B0                  # {motion pack, moveset, move list} by row, in the game image
                                          # (game/tekken.img, loaded at 0x82000000)
IMAGE_BASE = 0x82000000
ALO_END = b'AL_EFFECT\0'
BODY_ANIM = 0x4000                        # a move's animation id: 0x4000 + body animation (0x8000 +: the common ones)


def moveset(arc, image):
    key = struct.unpack_from('>I', image, MOTION_ROWS - IMAGE_BASE + 12 * DONOR_ROW + 4)[0]
    ms = bytearray(arc.read(key))
    ids = struct.unpack_from('>4h', ms, 0xF8 + 64)
    if ids != (DONOR_ID - 1, -(DONOR_ID - 1), DONOR_ID, -DONOR_ID):
        raise ValueError('motion row %d is not Marduk\'s moveset (ids %s)' % (DONOR_ROW, ids))
    struct.pack_into('>4h', ms, 0xF8 + 64, ID - 1, -(ID - 1), ID, -ID)
    m = motbin.read(bytes(ms))
    table = motbin.BASE + m.table_info['moves'][0]
    guards = [i for i in range(len(m.tables['moves']))
              if m.move_name(i).startswith('sGrd_') and m.anim_name(i).startswith('Bco_gurd_')]
    for i in guards:
        struct.pack_into('>I', ms, table + i * motbin.TTT2['moves'][0] + 8, BODY_ANIM + GUARD_ANIM)
    print('his guard (%#x) in %d standing guard moves' % (BODY_ANIM + GUARD_ANIM, len(guards)))
    return attacks.edit_moveset(motbin.read(bytes(ms)))


def effects(arc, donor=DONOR, code=CODE):
    """{path under the overlay: bytes}: the donor's (Marduk's) effect files and their textures under the code (Rick's)."""
    out = {}
    names = itemdb.effect_names(arc.read_name(donor + '.xml'))
    for name in names:
        src = '%s/alo/%s.alo' % (donor, name)
        if not arc.has(arc_key(src)):
            continue
        data = arc.read_name(src)
        out['%s/alo/%s.alo' % (code, name)] = data
        at = data.find(ALO_END)
        for t in (data[at + len(ALO_END):].split(b'\0') if at >= 0 else []):
            if t.endswith(b'.nut'):
                tex = '%s/alo/texture/%s' % (donor, t.decode('latin1'))
                if arc.has(arc_key(tex)):
                    out['%s/alo/texture/%s' % (code, t.decode('latin1'))] = arc.read_name(tex)
    return out, names


def arc_key(name):
    from ..ttt2.archive import key_of
    return key_of(name)


def main(game, rick, out, art=None):
    arc = Archives(game)
    folder = game if os.path.isdir(os.path.join(game, 'game')) is False else os.path.join(game, 'game')
    image = open(os.path.join(folder, 'tekken.img'), 'rb').read()
    files = {}
    for ext in ('nud', 'nut', 'bon', 'xml'):
        files['%s.%s' % (CODE, ext)] = open(os.path.join(rick, 'files', '%s.%s' % (DONOR, ext)), 'rb').read()
    files['%s_blood.nut' % CODE] = open(os.path.join(rick, 'files', '%s_blood.nut' % DONOR), 'rb').read()
    files['key_%08x.bin' % MOVESET_KEY] = moveset(arc, image)
    if os.environ.get('RICK_CUSTOMIZE') == '1':     # Rick's cell in Customize: selecting him still hangs there
        files.update(menus.files(arc))
    fx, names = effects(arc)
    files.update(fx)
    if art:
        root = os.path.join(art, 'files')
        for r, _, fs in os.walk(root):
            for f in fs:
                rel = os.path.relpath(os.path.join(r, f), root).replace(os.sep, '/')
                files[rel] = open(os.path.join(r, f), 'rb').read()
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
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    main(*sys.argv[1:])
