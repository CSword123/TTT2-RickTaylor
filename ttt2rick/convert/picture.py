"""A fighter's picture (work/art/<name>.png) as the portrait, HUD and layout converters take it: RGBA, transparent
around the figure.

A picture that already has transparency (Rick's) is used as it is. An opaque one on a plain background (Jennifer's:
black) is cut out: the pixels joined to the border whose colour is within CUT of the border's are background (a flood
fill, so dark clothes inside the figure stay), and so is any enclosed patch of that colour of HOLE pixels or more (the
gaps between an arm and the body); the figure's anti-aliased fringe, within FRINGE of it, fades out.
"""
from collections import deque

import numpy as np
from PIL import Image

CUT = 6                 # colour distance (max over channels) from the border colour that is still background
FRINGE = 14             # and up to which the edge pixels next to it fade in
HOLE = 150              # pixels: an enclosed patch of background colour this big is background too


def load(path):
    return cut_out(Image.open(path).convert('RGBA'))


def cut_out(img):
    a = np.asarray(img)
    if (a[..., 3] < 255).any():
        return img
    rgb = a[..., :3].astype(np.int16)
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg_colour = np.median(border, 0)
    dist = np.abs(rgb - bg_colour).max(-1)
    h, w = dist.shape
    flat = dist <= CUT
    bg = np.zeros((h, w), bool)
    seen = np.zeros((h, w), bool)
    for y0, x0 in zip(*np.nonzero(flat)):          # each patch of background colour: joined to the border, or big
        if seen[y0, x0]:
            continue
        patch, edge, q = [], False, deque([(y0, x0)])
        seen[y0, x0] = True
        while q:
            y, x = q.popleft()
            patch.append((y, x))
            edge |= y in (0, h - 1) or x in (0, w - 1)
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < h and 0 <= xx < w and flat[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True
                    q.append((yy, xx))
        if edge or len(patch) >= HOLE:
            ys, xs = zip(*patch)
            bg[list(ys), list(xs)] = True
    near = np.zeros_like(bg)                   # the figure's pixels touching the background: its fringe
    near[1:] |= bg[:-1]
    near[:-1] |= bg[1:]
    near[:, 1:] |= bg[:, :-1]
    near[:, :-1] |= bg[:, 1:]
    alpha = np.where(bg, 0, 255).astype(np.float32)
    fringe = near & ~bg
    alpha[fringe] = 255 * np.clip((dist[fringe] - CUT) / (FRINGE - CUT), 0, 1)
    out = a.copy()
    out[..., 3] = alpha.astype(np.uint8)
    return Image.fromarray(out)
