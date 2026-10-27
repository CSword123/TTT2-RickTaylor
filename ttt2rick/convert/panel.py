"""The added fighters' costume panel pictures in Customize (the slot screen's two 124 x 304 pictures, costume A and B),
from their pictures (ttt2rick.convert.fighters).

python -m ttt2rick.convert.panel <game folder> <out dir>

The title keeps each fighter's two in an NTXR file of its own, by a 63-entry key table by internal id (0x8200C7D0,
read by sub_8227A078); recomp/runtime/rick_slot.cpp gives an added fighter's id the key of its file here,
`<code>/costume_panel.nut` (PANEL_NAME). Each picture is the fighter's picture, its blood cleaned off (Rick's), fitted
to the panel's height on the stock panels' backdrop: per row, the colour at the panels' left and right edges (where
no fighter stands), the median over every stock panel (black above, the floor's grey below). Costume B's is the same
picture, or the fighter's `panel_b` when costume B has a body of its own (Rick's Mirror Rick).
Writes <out>/files/<code>/costume_panel.nut for ttt2rick.ttt2.overlay, and <code>_costume_panel.png to look at.
"""
import os
import struct
import sys

import numpy as np
from PIL import Image

from ..ttt2 import xbox
from ..ttt2.archive import Archives
from ..ttt2.petexy import nut
from . import picture
from .fighters import ADDED

PANEL_KEYS = 0x8200C7D0          # 63 x the key of a fighter's costume panel NTXR, by internal id (game image)
IMAGE_BASE = 0x82000000
PANEL_NAME = '%s/costume_panel.nut'
W, H = 124, 304
EDGE = 8                         # columns at each side that are backdrop
TOP, BOTTOM = 10, 4              # margins of the figure in the panel
FIRST_GIDX = 116                 # the stock panels' textures are numbered 1..115


def backdrop(arc, image):
    keys = [struct.unpack_from('>I', image, PANEL_KEYS - IMAGE_BASE + 4 * i)[0] for i in range(63)]
    pics = [xbox.decode_texture(t)[..., :3].astype(np.float32) for k in keys if arc.has(k)
            for t in xbox.read_nut(arc.read(k))['textures']]
    edges = np.concatenate([p[:, :EDGE] for p in pics] + [p[:, -EDGE:] for p in pics], 1)
    rows = np.median(edges, 1)                          # (H, 3)
    return np.repeat(rows[:, None], W, 1), keys


def panel(bg, figure):
    """The figure (RGBA PIL image) fitted to the panel's height, centred, over the backdrop."""
    box = figure.getbbox()
    figure = figure.crop(box)
    scale = (H - TOP - BOTTOM) / figure.height
    figure = figure.resize((max(1, int(round(figure.width * scale))), H - TOP - BOTTOM), Image.LANCZOS)
    out = Image.fromarray(bg.astype(np.uint8)).convert('RGBA')
    out.alpha_composite(figure, ((W - figure.width) // 2, TOP))
    return np.asarray(out)


def main(game, out):
    arc = Archives(game)
    folder = os.path.join(game, 'game') if os.path.isdir(os.path.join(game, 'game')) else game
    image = open(os.path.join(folder, 'tekken.img'), 'rb').read()
    bg, keys = backdrop(arc, image)
    template = xbox.read_nut(arc.read(keys[17]))         # Marduk's: the panel textures' format and fields
    for k, f in enumerate(ADDED):
        pic = picture.load(f.picture_path())
        pic = f.variants(pic)[0][0]                     # the clean picture
        rgba = panel(bg, pic)
        b = getattr(f, 'panel_b', None)                 # costume B's own picture, or A's
        rgba_b = panel(bg, picture.load(os.path.join(os.path.dirname(f.picture_path()), b))) if b else rgba
        if b:
            Image.fromarray(rgba_b).save(os.path.join(out, '%s_costume_panel_b.png' % f.code))
        textures = []
        for j, t in enumerate(template['textures']):    # costume A and B
            new = nut.make_texture(rgba_b if j else rgba, FIRST_GIDX + 2 * k + j, fmt=t['fmt'], mips=1)
            textures.append(dict(t, ext=None, **{key: new[key] for key in ('mips', 'gidx', 'w', 'h', 'fmt')}))
        data = xbox.write_nut(dict(template, textures=textures))
        path = os.path.join(out, 'files', PANEL_NAME % f.code)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(data)
        Image.fromarray(rgba).save(os.path.join(out, '%s_costume_panel.png' % f.code))
        print('%s: %s, %d bytes (textures %d, %d)' % (f.name, PANEL_NAME % f.code, len(data), FIRST_GIDX + 2 * k,
                                                     FIRST_GIDX + 2 * k + 1))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
