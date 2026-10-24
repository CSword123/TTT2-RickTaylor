"""Rick's big select portraits (356x612, player 1 red frame, player 2 blue and mirrored) from a picture of him.

python -m ttt2rick.convert.portrait <game folder> <picture.png (RGBA, transparent around him)> <out dir>

The frames and panels come from the game's own portraits (container 6CCDFC60, data003: 118 NUTs, two per UI
position): the median of each side's 59 gives the frame glow, the frame splits the outside from the panel, and the
panel gets one dark colour. Rick is cut to the panel and the frame drawn over him (nothing of him outside it),
placed and scaled like a bust: head top at HEAD_TOP, the picture's width scaled by SCALE. Writes
portrait_1p.png and portrait_2p.png, and the game's single-file form of each (a NUT like Marduk's own,
`ric/portrait_1p.nut` and `ric/portrait_2p.nut` under <out>/files, for ttt2rick.ttt2.overlay; recomp/runtime/
rick_slot.cpp gives them to the screens that show Rick), and a green-framed one like the game's alternate
(illustrated) portraits, portrait_green.png / ric/portrait_green.nut. The select screen's container gets Rick's two
after its own (frames 118 and 119, CONTAINER_RICK; key_6ccdfc60.bin), which rick_slot.cpp shows for his row.
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

CONTAINER = 0x6CCDFC60
KEY_TABLE = 0x820CD408          # in the game image: 59 x {player 1 key, player 2 key}, by UI row
DONOR_ROW = 18                  # Marduk's UI row
CONTAINER_RICK = 118            # his frames in the container (player 1, player 2): rick_slot.cpp kPortraitFrame
SIZE = (356, 612)
PANEL = (24, 24, 27, 240)       # the panels' dark grey
SCALE = 0.70                    # of the picture's pixels
HEAD_TOP, CENTRE_X = 18, 182    # where the picture's top and centre land
FRINGE = 5                      # px of the picture's dark cut-out edge trimmed off


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


def compose(med, frame, inside, picture, mirror):
    base = np.where(frame[..., None], med, 0).astype(np.float32)
    base[inside] = PANEL
    a = picture.getchannel('A').filter(ImageFilter.MinFilter(2 * FRINGE + 1)).filter(ImageFilter.GaussianBlur(1.5))
    picture = picture.copy()
    picture.putalpha(a)
    pic = picture.resize((round(picture.width * SCALE), round(picture.height * SCALE)), Image.LANCZOS)
    layer = Image.new('RGBA', SIZE)
    layer.paste(pic, (CENTRE_X - pic.width // 2, HEAD_TOP))
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


def main(game, picture, out):
    arc = Archives(game)
    P = portraits(arc)
    pic = Image.open(picture).convert('RGBA')
    os.makedirs(out, exist_ok=True)
    textures = []
    for side in (0, 1):
        med = np.median(P[side::2].astype(np.int16), 0).astype(np.uint8)
        if side == 1:                   # the blue side is the red one mirrored: compose unmirrored, then flip
            med = med[:, ::-1]
        frame, inside = masks(med, side)
        img = compose(med, frame, inside, pic, mirror=side == 1)
        Image.fromarray(img).save(os.path.join(out, 'portrait_%dp.png' % (side + 1)))
        textures.append(img)
    folder = os.path.join(game, 'game') if os.path.isdir(os.path.join(game, 'game')) else game
    image = open(os.path.join(folder, 'tekken.img'), 'rb').read()
    G = green_portraits(arc, image)
    med = np.median(G.astype(np.int16), 0).astype(np.uint8)
    frame, inside = masks(med, 2)
    green = compose(med, frame, inside, pic, mirror=False)
    Image.fromarray(green).save(os.path.join(out, 'portrait_green.png'))
    # the single files: Marduk's, its texture replaced
    for side, img in enumerate(textures):
        key = struct.unpack_from('>I', image, KEY_TABLE - 0x82000000 + 4 * (2 * DONOR_ROW + side))[0]
        donor = xbox.read_nut(arc.read(key))
        t = donor['textures'][0]
        new = nut.make_texture(img, t['gidx'], t['fmt'], mips=len(t['mips']))
        donor['textures'][0] = dict(t, mips=new['mips'])
        path = os.path.join(out, 'files', 'ric', 'portrait_%dp.nut' % (side + 1))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(xbox.write_nut(donor))
        if side == 0:
            donor['textures'][0] = dict(t, mips=nut.make_texture(green, t['gidx'], t['fmt'], mips=len(t['mips']))['mips'])
            open(os.path.join(out, 'files', 'ric', 'portrait_green.nut'), 'wb').write(xbox.write_nut(donor))
    # the select screen's container: Rick's two frames after its own, made from Marduk's
    items = container_items(arc.read(CONTAINER))
    if len(items) != CONTAINER_RICK:
        raise ValueError('the portrait container has %d frames, not %d' % (len(items), CONTAINER_RICK))
    for side, img in enumerate(textures):
        donor = xbox.read_nut(items[2 * DONOR_ROW + side])
        t = donor['textures'][0]
        donor['textures'][0] = dict(t, mips=nut.make_texture(img, t['gidx'], t['fmt'], mips=len(t['mips']))['mips'])
        items.append(xbox.write_nut(donor))
    open(os.path.join(out, 'files', 'key_%08x.bin' % CONTAINER), 'wb').write(build_container(items))
    print(os.path.join(out, 'portrait_1p.png'), os.path.join(out, 'portrait_2p.png'))
    return textures


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
