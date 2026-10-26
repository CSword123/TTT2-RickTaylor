"""The added fighters' labels in the 2D layouts (loading and VS screens, select screen, results...), with their
pictures (ttt2rick.convert.fighters: Rick's, then Jennifer's; one run, since they share the layouts).

python -m ttt2rick.convert.layouts <game folder> <out dir>

A per-fighter picture in a layout (LMB, data007, each followed by its texture container) is a sprite with one label
per fighter (`chara_face_mar`, `p1_chara_waku_mar`, `face_mar_lose`); the game jumps to the label of the fighter it
shows. Every layout with Marduk's labels gets each added fighter's beside them (`chara_face_ric`, `chara_face_jen`,
...), showing its pictures, made like the other fighters' at that place (ttt2rick.ttt2.petexy.art.Layout: frame and
background from theirs, its picture placed so its face sits where theirs do), on new texture pages appended to the
layout's container. The names (`chara_name_s_`, the frames' `p<n>_chara_waku_` labels end on the name) are its name
in the title's lettering. The select grids get each one's panel (`face_panel_ric`, Eddy's cloned with his picture,
in the top row above Eddy's; `face_panel_jen` above Lee's, right of Rick's), its picture inside the panel's frame
(art.in_frame), and the right grille (`spacer_right`) that covered the cells stops after them (Layout.fit_spacer).
recomp/runtime/rick_slot.cpp turns Marduk's labels into these while the game shows an added fighter.
Writes <out>/files/key_<layout>.bin and key_<container>.bin (for ttt2rick.ttt2.overlay).
"""
import os
import re
import sys

import numpy as np
from PIL import Image

from ..ttt2 import xbox
from ..ttt2.archive import Archives
from ..ttt2.petexy import art, lmb
from . import picture as picture_file
from .fighters import ADDED

LAYOUTS = 'data007.bin'
# The select grids' icons (56 x 88): closer than Layout's general head-and-shoulders place for tall pictures, as each
# fighter's icon says (Rick's: a close-up of the face, as the game's are measured: eyes 40% down, eyes to chin 30%)
ICON_SIZE = (56, 88)


class Sources:
    """A fighter's picture with where its face is, as ttt2rick.ttt2.petexy.art.Layout asks for it."""

    def __init__(self, fighter, letters=None):
        self.picture = art._float(picture_file.load(fighter.picture_path()))
        self.face, self.name, self.icon = fighter.face, fighter.name, fighter.icon + ('bust',)
        self.letters = letters

    def framed(self, place, w, h, mirror=False):
        """The picture scaled and moved so that the face sits at `place` in a w x h picture."""
        if (w, h) == ICON_SIZE:
            place = self.icon
        fx, fy, chin, _ = place
        img = self.picture
        ex, ey, ec = self.face
        if mirror:
            img = img[:, ::-1]
            ex = img.shape[1] - ex
            fx = 1.0 - fx
        scale = chin * h / ec
        sw, sh = max(1, round(img.shape[1] * scale)), max(1, round(img.shape[0] * scale))
        scaled = art._resize(img, sw, sh)
        out = np.zeros((h, w, 4), np.float32)
        x0, y0 = round(ex * scale - fx * w), round(ey * scale - fy * h)
        sx0, sy0, sx1, sy1 = max(x0, 0), max(y0, 0), min(x0 + w, sw), min(y0 + h, sh)
        if sx1 > sx0 and sy1 > sy0:
            out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = scaled[sy0:sy1, sx0:sx1]
        return out

    def title_name(self, w, h):
        pic = self.letters.picture(self.name) if self.letters is not None else None
        if pic is None:
            raise ValueError('no lettering learnt for %s' % self.name)
        if pic.shape[0] != h:
            pic = art._resize(pic, max(1, round(pic.shape[1] * h / pic.shape[0])), h)
        return pic


def codes_in(lm):
    """The fighter codes of a layout's per-fighter labels."""
    found = set()
    for s in lm.symbols:
        m = re.match(r'^(?:.*_)?face_panel_([a-z]{2,3})$', s) or re.match(r'^face_([a-z]{2,3})$', s)
        if m:
            found.add(m.group(1))
    return found


def main(game, out):
    arc = Archives(game)
    idx = arc.indices[LAYOUTS]
    blobs = {}
    codes = set()
    for i in range(len(idx) - 1):
        d = arc.entry(LAYOUTS, i)
        if d[:4] == b'LMB\0' and arc.entry(LAYOUTS, i + 1)[:4] == b'NTXR':
            blobs[i] = d
            codes |= codes_in(lmb.Lmb.read(d))
    added = {f.code for f in ADDED}
    codes = [art.DONOR] + sorted(codes - {art.DONOR} - added)
    sources = [Sources(f) for f in ADDED]
    letters = None
    for i, d in blobs.items():                  # the lettering, from the select screen's names
        if b'p1_chara_waku_' + art.DONOR.encode() in d:
            lay = art.Layout(lmb.Lmb.read(d), xbox.read_nut(arc.entry(LAYOUTS, i + 1)), sources[0], art.DONOR, codes)
            letters = art.Letters.of_layout(lay)
            if letters is not None:
                break
    os.makedirs(out, exist_ok=True)
    for f, src in zip(ADDED, sources):
        src.letters = letters
        name = letters.picture(f.name) if letters else None
        if name is None:
            raise ValueError('could not put %s together from the layouts\' names' % f.name)
        Image.fromarray(art._uint8(name)).save(os.path.join(out, '%s_layout_name.png' % f.code))
    dest = os.path.join(out, 'files')
    os.makedirs(dest, exist_ok=True)
    count = 0
    for i, d in blobs.items():
        lm = lmb.Lmb.read(d)
        if not any(art.code_label(s, ADDED[0].code) for s in lm.symbols) and \
                not any('face_panel_' + f.cell['anchor'] in lm.symbols for f in ADDED):
            continue
        textures = xbox.read_nut(arc.entry(LAYOUTS, i + 1))
        changed = False
        for f, src in zip(ADDED, sources):     # one after the other on the same layout: the fighters' own pages
            layout = art.Layout(lm, textures, src, f.code, codes, f.cell)
            layout.add_labels()
            layout.add_cell()
            if not layout.changed:
                continue
            changed = True
            pages = layout.pages()
            for tex in pages:
                for shape in lm.shapes():
                    for g in shape.graphics:
                        if g.atlas is None:
                            g.atlas = tex['gidx']
            textures['textures'] += pages
        if not changed:
            continue
        key, tkey = idx[i][0], idx[i + 1][0]
        open(os.path.join(dest, 'key_%08x.bin' % key), 'wb').write(lm.write())
        open(os.path.join(dest, 'key_%08x.bin' % tkey), 'wb').write(xbox.write_nut(textures))
        count += 1
    print('%s: %s\'s labels in %d layouts' % (dest, ' and '.join(f.name for f in ADDED), count))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
