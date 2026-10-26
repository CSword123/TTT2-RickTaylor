"""The added fighters' pictures in the fights' HUD (ttt2rick.convert.fighters): each one's face (140x140, player 1's
and player 2's mirrored) and name, appended to the HUD's texture container.

python -m ttt2rick.convert.hud <game folder> <out dir>

The HUD's pictures are textures of one container (7C476BDE, data003: 259 textures) by numbers from a table of the
title (HUD_NUMBERS: 59 x {name, face of player 1, face of player 2}, by UI row; Marduk's 48, 123, 182). Each added
fighter's three go after the container's own (Rick's 259, 260 and 261, Jennifer's 262-264: the fighter's hud);
recomp/runtime/rick_slot.cpp gives them for Marduk's while the HUD works on that fighter. The name is put together
from the other names' letters (the same chrome font; the fighter's hud_letters): each letter is cut at the middle of
the gaps beside it, and the dark glow around the word is drawn again at its ends. The face is the fighter's head from
its picture, faded out at the shoulders like the game's faces.
Writes <out>/files/key_7c476bde.bin (for ttt2rick.ttt2.overlay) and <code>_hud_face.png, <code>_hud_name.png to look at.
"""
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageFilter

from ..ttt2 import xbox
from ..ttt2.archive import Archives
from ..ttt2.petexy import nut
from . import picture as picture_file
from .fighters import ADDED

CONTAINER = 0x7C476BDE
HUD_NUMBERS = 0x82DDD2F0        # in the game image
DONOR_ROW = 18                  # Marduk's UI row
FIRST_ADDED = 259               # the container's own textures end here
NAME_FIRST = 30                 # the names are textures 30..88, by UI row
NAME_LEFT, NAME_GAP, NAME_RIGHT = 12, 3, 9      # where the first letter's core starts; between cores; after the last
FACE = 140
FACE_AT = (70, 16)              # where the fighter's head middle and top (its hud_face) land in the face


def core(a):
    """The letters' own pixels (bright, opaque), not their glow."""
    return (a[..., 3] > 200) & (a[..., :3].max(-1) > 120)


def name_texture(textures, letters):
    sources = {row: xbox.decode_texture(textures[NAME_FIRST + row]) for row, _, _ in letters}
    pieces = []
    for row, x0, x1 in letters:
        a = sources[row]
        cols = core(a).any(0)
        left, right = x0, x1                    # out to the middle of the gaps (or as far as the glow goes)
        while left > 0 and not cols[left - 1] and x0 - left < 6:
            left -= 1
        while right < a.shape[1] and not cols[right] and right - x1 < 6:
            right += 1
        mid_l = x0 - (x0 - left) // 2 if left > 0 and cols[left - 1] else x0 - 1
        mid_r = x1 + (right - x1) // 2 if right < a.shape[1] and cols[right] else x1 + 1
        pieces.append((a[:, mid_l:mid_r], x0 - mid_l, x1 - mid_l))
    width = NAME_LEFT + sum(p[2] - p[1] for p in pieces) + NAME_GAP * (len(pieces) - 1) + NAME_RIGHT
    width = (width + 3) // 4 * 4
    out = np.zeros((pieces[0][0].shape[0], width, 4), np.float32)
    x = NAME_LEFT
    for piece, c0, c1 in pieces:
        at = x - c0
        w = piece.shape[1]
        lo, hi = max(0, at), min(width, at + w)
        src = piece[:, lo - at:hi - at].astype(np.float32)
        dst = out[:, lo:hi]
        sa, da = src[..., 3:] / 255.0, dst[..., 3:] / 255.0
        a = sa + da * (1 - sa)
        dst[..., :3] = np.where(a > 0, (src[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(a, 1e-6), 0)
        dst[..., 3:] = a * 255
        x += (c1 - c0) + NAME_GAP
    # the glow at the word's ends: black, from the letters' shape
    shape = Image.fromarray((core(out.astype(np.uint8)) * 255).astype(np.uint8))
    glow = np.asarray(shape.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(3.2)), np.float32)
    glow = np.clip(glow * 1.9, 0, 255)[..., None]
    a = out[..., 3:]
    rgb = out[..., :3] * (a / 255.0)            # the letters over the glow
    alpha = a + glow * (1 - a / 255.0)
    out[..., :3] = np.where(alpha > 0, rgb / np.maximum(alpha / 255.0, 1e-6), 0)
    out[..., 3:] = alpha
    return out.clip(0, 255).astype(np.uint8)


def face_texture(picture, place):
    scale, cx, top = place
    pic = picture.resize((round(picture.width * scale), round(picture.height * scale)), Image.LANCZOS)
    layer = Image.new('RGBA', (FACE, FACE))
    layer.paste(pic, (FACE_AT[0] - round(cx * scale), FACE_AT[1] - round(top * scale)))
    out = np.asarray(layer).astype(np.float32)
    # faded out at the shoulders and the sides, as the game's faces are
    y, x = np.mgrid[0:FACE, 0:FACE].astype(np.float32)
    fade = np.clip((136 - y) / 40, 0, 1) * np.clip(np.minimum(x, FACE - 1 - x) / 22, 0, 1)
    out[..., 3] *= fade
    return out.clip(0, 255).astype(np.uint8)


def main(game, out):
    arc = Archives(game)
    folder = os.path.join(game, 'game') if os.path.isdir(os.path.join(game, 'game')) else game
    image = open(os.path.join(folder, 'tekken.img'), 'rb').read()
    donor = struct.unpack_from('>3I', image, HUD_NUMBERS - 0x82000000 + 12 * DONOR_ROW)
    container = xbox.read_nut(arc.read(CONTAINER))
    textures = container['textures']
    if len(textures) != FIRST_ADDED:
        raise ValueError('the HUD container has %d textures, not %d' % (len(textures), FIRST_ADDED))
    os.makedirs(out, exist_ok=True)
    for f in ADDED:
        if len(textures) != f.hud[0]:
            raise ValueError('%s\'s HUD pictures would be %d.., not %d' % (f.code, len(textures), f.hud[0]))
        name = name_texture(textures, f.hud_letters)
        face = face_texture(picture_file.load(f.picture_path()), f.hud_face)
        Image.fromarray(name).save(os.path.join(out, '%s_hud_name.png' % f.code))
        Image.fromarray(face).save(os.path.join(out, '%s_hud_face.png' % f.code))
        for k, (number, img) in enumerate(zip(f.hud, (name, face, face[:, ::-1]))):
            like = textures[donor[k]]
            new = nut.make_texture(np.ascontiguousarray(img), number + 1, like['fmt'], mips=len(like['mips']))
            textures.append(dict(like, w=img.shape[1], h=img.shape[0], gidx=number + 1, mips=new['mips'],
                                 ext=like['ext'][:-8] + struct.pack('>I', number + 1) + like['ext'][-4:]))
    path = os.path.join(out, 'files', 'key_%08x.bin' % CONTAINER)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(xbox.write_nut(container))
    print(path, 'textures', len(textures))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
