"""The added fighters' big select portraits (356x612, player 1 red frame, player 2 blue and mirrored) from their
pictures (ttt2rick.convert.fighters: Rick's, then Jennifer's).

python -m ttt2rick.convert.portrait <game folder> <out dir>

The frames and panels come from the game's own portraits (container 6CCDFC60, data003: 118 NUTs, two per UI
position): the median of each side's 59 gives the frame glow, the frame splits the outside from the panel, and the
panel gets one dark colour. Rick is cut to the panel and the frame drawn over him (nothing of him outside it),
placed and scaled like a bust (the fighter's `portrait`: the picture's scale, and its point put at the middle,
HEAD_TOP from the top). Writes <code>_portrait_1p.png and _2p.png, and the game's single-file form of each (a NUT
like Marduk's own, `<code>/portrait_1p.nut` and `<code>/portrait_2p.nut` under <out>/files, for ttt2rick.ttt2.overlay;
recomp/runtime/rick_slot.cpp gives them to the screens that show the fighter), and a green-framed one like the
game's alternate (illustrated) portraits, <code>_portrait_green.png / <code>/portrait_green.nut. The select screen's
container gets each fighter's two after its own (key_6ccdfc60.bin; Rick's 118 and 119, CONTAINER_ADDED, then
Jennifer's 122 and 123: the fighter's portrait_frame), which rick_slot.cpp shows for its row.

Rick's picture's blood is taken off (ttt2rick.convert.clean.clean_picture); each of his portraits is also made with
it, named with _blood (ric_portrait_1p_blood.png, ric/portrait_1p_blood.nut, ..., container frames 120 and 121),
which rick_slot.cpp shows under TTT2_RICK_BLOOD=1.
"""
import os
import struct
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

from ..ttt2 import xbox
from ..ttt2.archive import Archives
from ..ttt2.petexy import nut
from . import picture as picture_file
from .fighters import ADDED

CONTAINER = 0x6CCDFC60
KEY_TABLE = 0x820CD408          # in the game image: 59 x {player 1 key, player 2 key}, by UI row
DONOR_ROW = 18                  # Marduk's UI row
CONTAINER_ADDED = 118           # the added fighters' frames in the container, from here on
SIZE = (356, 612)
PANEL = (24, 24, 27, 240)       # the panels' dark grey
HEAD_TOP, CENTRE_X = 18, 182    # where the fighter's portrait point lands


def container_items(d):
    n, = struct.unpack_from('>I', d, 0)
    return [d[o:o + s] for o, s in (struct.unpack_from('>II', d, 4 + 8 * i) for i in range(n))]


def build_container(items):
    head = 4 + 8 * len(items)
    out = bytearray(head + (-head % 16))
    struct.pack_into('>I', out, 0, len(items))
    for i, it in enumerate(items):
        out += bytes(-len(out) % 16)
        struct.pack_into('>II', out, 4 + 8 * i, len(out), len(it))
        out += it
    return bytes(out)


def portraits(arc):
    d = arc.read(CONTAINER)
    n, = struct.unpack_from('>I', d, 0)
    out = []
    for i in range(n):
        o, s = struct.unpack_from('>II', d, 4 + 8 * i)
        out.append(xbox.decode_texture(xbox.read_nut(d[o:o + s])['textures'][0]))
    return np.stack(out)


GREEN_TABLES = (0x820CD5E0, 0x820CD7B8, 0x820CD990)   # the alternate (illustrated) portraits: 59 x {key, 0}, green frames


def green_portraits(arc, image):
    out = []
    for t in GREEN_TABLES:
        for row in range(59):
            k = struct.unpack_from('>I', image, t - 0x82000000 + 8 * row)[0]
            if k and arc.has(k):
                out.append(xbox.decode_texture(xbox.read_nut(arc.read(k))['textures'][0]))
    return np.stack(out)


def masks(med, side):
    r, g, b, a = (med[..., i].astype(int) for i in range(4))
    if side == 2:
        glow = (a > 40) & (g - np.maximum(r, b) > 50)
    else:
        glow = (a > 40) & ((r - np.maximum(g, b) > 50) if side == 0 else (np.minimum(g, b) - r > 50))
    h, w = glow.shape
    outside = np.zeros_like(glow)
    q = deque([(y, x) for y in range(h) for x in (0, w - 1)] + [(y, x) for x in range(w) for y in (0, h - 1)])
    while q:
        y, x = q.popleft()
        if outside[y, x] or glow[y, x]:
            continue
        outside[y, x] = True
        for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= yy < h and 0 <= xx < w and not outside[yy, xx] and not glow[yy, xx]:
                q.append((yy, xx))
    near = np.asarray(Image.fromarray((outside * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(41))) > 0
    frame = glow & near
    return frame, ~outside & ~frame


def compose(med, frame, inside, picture, mirror, place, fringe):
    base = np.where(frame[..., None], med, 0).astype(np.float32)
    base[inside] = PANEL
    a = picture.getchannel('A').filter(ImageFilter.MinFilter(2 * fringe + 1)).filter(ImageFilter.GaussianBlur(1.5))
    picture = picture.copy()
    picture.putalpha(a)
    scale, px, py = place
    pic = picture.resize((round(picture.width * scale), round(picture.height * scale)), Image.LANCZOS)
    layer = Image.new('RGBA', SIZE)
    layer.paste(pic, (CENTRE_X - round(px * scale), HEAD_TOP - round(py * scale)))
    fig = np.asarray(layer).astype(np.float32)
    within = np.asarray(Image.fromarray((inside * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(
        ImageFilter.GaussianBlur(1)), np.float32) / 255.0
    fig[..., 3] *= within                       # only inside the frame
    fa = fig[..., 3:] / 255.0
    rgb = fig[..., :3] * fa + base[..., :3] * (1 - fa)
    alpha = np.maximum(base[..., 3:], fig[..., 3:])
    edge = np.where(frame[..., None], med, 0).astype(np.float32)        # the frame over him
    ea = edge[..., 3:] / 255.0
    rgb = edge[..., :3] * ea + rgb * (1 - ea)
    alpha = np.maximum(alpha, edge[..., 3:])
    out = np.concatenate([rgb, alpha], -1).clip(0, 255).astype(np.uint8)
    return out[:, ::-1] if mirror else out


def main(game, out):
    arc = Archives(game)
    P = portraits(arc)
    folder = os.path.join(game, 'game') if os.path.isdir(os.path.join(game, 'game')) else game
    image = open(os.path.join(folder, 'tekken.img'), 'rb').read()
    G = green_portraits(arc, image)
    items = container_items(arc.read(CONTAINER))
    if len(items) != CONTAINER_ADDED:
        raise ValueError('the portrait container has %d frames, not %d' % (len(items), CONTAINER_ADDED))
    for f in ADDED:
        if len(items) != f.portrait_frame:
            raise ValueError('%s\'s portraits would be frames %d.., not %d' % (f.code, len(items), f.portrait_frame))
        os.makedirs(os.path.join(out, 'files', f.code), exist_ok=True)
        for pic, suffix in f.variants(picture_file.load(f.picture_path())):
            textures = []
            for side in (0, 1):
                med = np.median(P[side::2].astype(np.int16), 0).astype(np.uint8)
                if side == 1:               # the blue side is the red one mirrored: compose unmirrored, then flip
                    med = med[:, ::-1]
                frame, inside = masks(med, side)
                img = compose(med, frame, inside, pic, side == 1, f.portrait, f.portrait_fringe)
                Image.fromarray(img).save(os.path.join(out, '%s_portrait_%dp%s.png' % (f.code, side + 1, suffix)))
                textures.append(img)
            med = np.median(G.astype(np.int16), 0).astype(np.uint8)
            frame, inside = masks(med, 2)
            green = compose(med, frame, inside, pic, False, f.portrait, f.portrait_fringe)
            Image.fromarray(green).save(os.path.join(out, '%s_portrait_green%s.png' % (f.code, suffix)))
            # the single files: Marduk's, its texture replaced
            for side, img in enumerate(textures):
                key = struct.unpack_from('>I', image, KEY_TABLE - 0x82000000 + 4 * (2 * DONOR_ROW + side))[0]
                donor = xbox.read_nut(arc.read(key))
                t = donor['textures'][0]
                new = nut.make_texture(img, t['gidx'], t['fmt'], mips=len(t['mips']))
                donor['textures'][0] = dict(t, mips=new['mips'])
                open(os.path.join(out, 'files', f.code, 'portrait_%dp%s.nut' % (side + 1, suffix)), 'wb').write(
                    xbox.write_nut(donor))
                if side == 0:
                    donor['textures'][0] = dict(t, mips=nut.make_texture(green, t['gidx'], t['fmt'], mips=len(t['mips']))['mips'])
                    open(os.path.join(out, 'files', f.code, 'portrait_green%s.nut' % suffix), 'wb').write(
                        xbox.write_nut(donor))
            # the select screen's container: the fighter's two frames after the ones before, from Marduk's
            for side, img in enumerate(textures):
                donor = xbox.read_nut(items[2 * DONOR_ROW + side])
                t = donor['textures'][0]
                donor['textures'][0] = dict(t, mips=nut.make_texture(img, t['gidx'], t['fmt'], mips=len(t['mips']))['mips'])
                items.append(xbox.write_nut(donor))
            print(os.path.join(out, '%s_portrait_1p%s.png' % (f.code, suffix)), 'frames', len(items) - 2, len(items) - 1)
    open(os.path.join(out, 'files', 'key_%08x.bin' % CONTAINER), 'wb').write(build_container(items))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
