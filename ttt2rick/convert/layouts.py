"""Rick's labels in the 2D layouts (loading and VS screens, select screen, results...), with his pictures.

python -m ttt2rick.convert.layouts <game folder> <picture.png (RGBA, transparent around him)> <out dir>

A per-fighter picture in a layout (LMB, data007, each followed by its texture container) is a sprite with one label
per fighter (`chara_face_mar`, `p1_chara_waku_mar`, `face_mar_lose`); the game jumps to the label of the fighter it
shows. Every layout with Marduk's labels gets Rick's beside them (`chara_face_ric`, ...), showing his pictures,
made like the other fighters' at that place (ttt2rick.ttt2.petexy.art.Layout: frame and background from theirs, his
picture placed so his face sits where theirs do), on a new texture page appended to the layout's container. The
names (`chara_name_s_`, the frames' `p<n>_chara_waku_` labels end on the name) are RICK in the title's lettering.
The select grids get Rick's panel (`face_panel_ric`, Eddy's cloned with his picture) in his cell, above Eddy's.
recomp/runtime/rick_slot.cpp turns Marduk's labels into these while the game shows Rick.
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

CODE, NAME = 'ric', 'RICK'
LAYOUTS = 'data007.bin'
# In the picture (work/art/rick_taylor.png): the eyes' centre and the eyes-to-chin distance, in its pixels
FACE = (466, 134, 98)
# Rick's select grid cell (rick_slot.cpp: top row, right of Violet): above Eddy's panel, in the top row
CELL = {'anchor': 'edd', 'columns': 0, 'grid_row': 0}
# The select grids' icons (56 x 88) are close-ups of the face (eyes 40% down, eyes to chin 30% of the height,
# measured on the game's): closer than Layout's general head-and-shoulders place for tall pictures
ICON_SIZE, ICON_PLACE = (56, 88), (0.50, 0.40, 0.30, 'bust')


class Sources:
    """Rick's picture with where his face is, as ttt2rick.ttt2.petexy.art.Layout asks for it."""

    def __init__(self, picture, letters=None):
        self.picture = art._float(Image.open(picture).convert('RGBA'))
        self.letters = letters

    def framed(self, place, w, h, mirror=False):
        """The picture scaled and moved so that the face sits at `place` in a w x h picture."""
        if (w, h) == ICON_SIZE:
            place = ICON_PLACE
        fx, fy, chin, _ = place
        img = self.picture
        ex, ey, ec = FACE
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
        pic = self.letters.picture(NAME) if self.letters is not None else None
        if pic is None:
            raise ValueError('no lettering learnt for %s' % NAME)
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


def main(game, picture, out):
    arc = Archives(game)
    idx = arc.indices[LAYOUTS]
    blobs = {}
    codes = set()
    for i in range(len(idx) - 1):
        d = arc.entry(LAYOUTS, i)
        if d[:4] == b'LMB\0' and arc.entry(LAYOUTS, i + 1)[:4] == b'NTXR':
            blobs[i] = d
            codes |= codes_in(lmb.Lmb.read(d))
    codes = [art.DONOR] + sorted(codes - {art.DONOR, CODE})
    sources = Sources(picture)
    for i, d in blobs.items():                  # the lettering, from the select screen's names
        if b'p1_chara_waku_' + art.DONOR.encode() in d:
            lay = art.Layout(lmb.Lmb.read(d), xbox.read_nut(arc.entry(LAYOUTS, i + 1)), sources, art.DONOR, codes)
            sources.letters = art.Letters.of_layout(lay)
            if sources.letters is not None:
                break
    name = sources.letters.picture(NAME) if sources.letters else None
    if name is None:
        raise ValueError('could not put %s together from the layouts\' names' % NAME)
    os.makedirs(out, exist_ok=True)
    Image.fromarray(art._uint8(name)).save(os.path.join(out, 'layout_name.png'))
    dest = os.path.join(out, 'files')
    os.makedirs(dest, exist_ok=True)
    count = 0
    for i, d in blobs.items():
        lm = lmb.Lmb.read(d)
        if not any(art.code_label(s, CODE) for s in lm.symbols) and 'face_panel_' + CELL['anchor'] not in lm.symbols:
            continue
        textures = xbox.read_nut(arc.entry(LAYOUTS, i + 1))
        layout = art.Layout(lm, textures, sources, CODE, codes, CELL)
        layout.add_labels()
        layout.add_cell()
        if not layout.changed:
            continue
        pages = layout.pages()
        for tex in pages:
            for shape in lm.shapes():
                for g in shape.graphics:
                    if g.atlas is None:
                        g.atlas = tex['gidx']
        textures['textures'] += pages
        key, tkey = idx[i][0], idx[i + 1][0]
        open(os.path.join(dest, 'key_%08x.bin' % key), 'wb').write(lm.write())
        open(os.path.join(dest, 'key_%08x.bin' % tkey), 'wb').write(xbox.write_nut(textures))
        count += 1
    print('%s: Rick\'s labels in %d layouts' % (dest, count))


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
