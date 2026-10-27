"""The 2D screens' per-fighter labels and pictures: Petexy's Wii U port (MIT, see LICENSE), tools/characters/ttt2char/
convert/art.py @ 581c048: the picture helpers, compose, the title's lettering (Letters) and Layout (a layout with a
fighter's labels added). Changes: the donor fighter is DONOR (Marduk, not Paul: the fighter whose labels are copied
for the new one); the new grid cell's place (Layout's `cell`) comes from the caller; Sources comes from the caller
(ttt2rick.convert.layouts), and nut is the Xbox 360 NTXR adapter's texture maker.
"""
import re

import numpy as np
from PIL import Image

from . import lmb, nut

DONOR = 'mar'
PAUL = DONOR                      # (the name the copied code uses)
# Labels whose pictures the game puts in itself (the big portraits' frames): copied, not drawn; they end on
# the fighter's name, which is drawn.
GAME_DRAWN = re.compile(r'^p[12]_chara_waku_$')
# The select grids' new cell (add_cell): at a fighter's panel (`anchor`) moved some columns over (the columns'
# pitch: between the panels of PITCH_FROM), in the top row (the height of GRID_BESIDE's panel) or the anchor's own row.
GRID_BESIDE = 'vio'
PITCH_FROM = ('rog', 'rav')       # grid row 1, columns 0 and 1
PAGE_WIDTH = 1024                 # new texture pages: at most this wide, as tall as needed
SPACER_EDGE = 24                  # texels: a grille's bevelled inner edge, kept when it is shortened
SPACER_FADE = 6                   # texels blended across a shortened grille's cut


def cut_columns(pic, k, edge_high):
    """A grille's picture with k texel columns of its band cut out (Layout.shorten_spacer). The band darkens towards
    its inner edge (high u with edge_high, else low u), so the cut goes where the columns on either side of it are
    alike in brightness (k is whole periods of the perforation, so the holes line up), between the edge
    (SPACER_EDGE) and the L's lower part (the columns its bottom rows have), and the seam is blended."""
    h, w = pic.shape[:2]
    alpha = pic[..., 3] if pic.shape[2] == 4 else np.ones((h, w))
    lower = np.nonzero(alpha[h - 5] > 0)[0]
    if edge_high:
        lo, hi = (lower.max() + 8 if len(lower) else SPACER_EDGE), w - SPACER_EDGE - k
    else:
        lo, hi = SPACER_EDGE, (lower.min() - 8 if len(lower) else w - SPACER_EDGE) - k
    if hi < lo + SPACER_FADE:                   # no room: just before the edge
        s = w - SPACER_EDGE - k if edge_high else SPACER_EDGE
    else:
        band = alpha[:, (lo + hi) // 2] > 0     # the band's rows
        lum = pic[band][..., :3].mean(-1)
        diff = [abs(lum[:, s - SPACER_FADE:s].mean() - lum[:, s + k:s + k + SPACER_FADE].mean())
                for s in range(lo, hi + 1)]
        s = lo + int(np.argmin(diff))
    new = np.concatenate([pic[:, :s], pic[:, s + k:]], 1)
    for i in range(min(SPACER_FADE, s)):        # the columns before the cut fade into the ones after it
        t = (i + 1) / (SPACER_FADE + 1)
        c = s - SPACER_FADE + i
        if c >= 0:
            new[:, c] = (1 - t) * pic[:, c] + t * pic[:, c + k]
    return new

# Where a face sits in each kind of picture: (eyes' centre x, y as fractions of the picture, eyes-to-chin as a
# fraction of its height, which Tekken 7 picture: 'bust' or 'body'). Measured on the TTT2 pictures.
FACE_TALL = (0.52, 0.40, 0.21, 'bust')          # 56x88, 100x136: head and shoulders
FACE_SQUARE = (0.40, 0.38, 0.20, 'bust')        # 140x140
FACE_STRIP = (0.46, 0.42, 0.36, 'bust')         # 160x56: eyes and mouth, faded at the sides
FACE_BAR = (0.15, 0.40, 0.36, 'bust')           # 120x40 .. 200x48: a face at the left end of a bar
FACE_BANNER = (0.56, 0.43, 0.29, 'bust')        # 548x140
FACE_BODY = (0.45, 0.13, 0.08, 'body')          # 460x480: the whole fighter
FACE_PORTRAIT = (0.47, 0.17, 0.105, 'body')     # 356x612: down to the hips
FACE_HUD = (0.50, 0.42, 0.24, 'bust')           # 140x140 in fights: head and shoulders


def face_place(w, h):
    a = w / h
    if w >= 300 and h >= 300:
        return FACE_BODY if a > 0.75 else FACE_PORTRAIT
    if a >= 3.2 and h >= 100:
        return FACE_BANNER
    if a >= 2.4:
        return FACE_STRIP if a < 3.0 and h >= 50 else FACE_BAR
    if a >= 0.85:
        return FACE_SQUARE
    return FACE_TALL



def _float(img):
    return np.asarray(img, np.float32) / 255.0


def _uint8(a):
    return np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)


def _premultiplied(a):
    out = a.copy()
    out[..., :3] *= out[..., 3:4]
    return out


def _straight(p):
    out = p.copy()
    alpha = out[..., 3:4]
    out[..., :3] = np.where(alpha > 1e-4, out[..., :3] / np.maximum(alpha, 1e-4), 0.0)
    return out


def _resize(a, w, h):
    """An RGBA float picture resized (premultiplied, so edges do not darken or bleed)."""
    p = _premultiplied(a)
    chans = [np.asarray(Image.fromarray(p[..., c]).resize((w, h), Image.LANCZOS)) for c in range(4)]
    return _straight(np.clip(np.stack(chans, -1), 0.0, 1.0))



def compose(others, picture):
    """A picture like `others` (N, h, w, 4 floats: every fighter's picture for the place) with `picture` (h, w, 4)
    in it: where all of them agree (a frame, a background they share) theirs, elsewhere `picture` cut to the area
    theirs cover, over their darkest and most transparent pixels."""
    n = len(others)
    spread = others.std(0).max(-1)
    shared = spread < 0.04
    mean = others.mean(0)
    # the background: per pixel, the mean of the quarter of the pictures darkest there (transparent is darkest)
    weight = others[..., 3] * (0.25 + others[..., :3].mean(-1))
    order = np.argsort(weight, axis=0)[:max(1, n // 4)]
    background = np.take_along_axis(others, order[..., None], 0).mean(0)
    cover = np.percentile(others[..., 3], 85, axis=0)
    p = picture.copy()
    p[..., 3] *= cover
    out = _over(p, background)
    out[shared] = mean[shared]
    return out


def in_frame(picture, panel):
    """A grid icon `picture` inside the frame of the empty `panel` (the shape every grid panel shows: a black edge
    with a white line inside it on the sides and the bottom, fading out upwards, around a see-through grey): the
    title's icons are their fighter cut to the frame, with the frame's edges drawn over him, and only the head
    rising out of its open top. Below the frame's top the picture is cut to its outer edges, and the frame drawn on it."""
    a = panel[..., 3]
    h, w = a.shape
    inner = panel[h * 3 // 4, w // 2]                       # the see-through grey inside it
    alike = (np.abs(a - inner[3]) < 0.05) & (np.abs(panel[..., :3] - inner[:3]).max(-1) < 0.05)
    cols, rows = np.nonzero(alike[h * 3 // 4])[0], np.nonzero(alike[:, w // 2])[0]
    if not len(cols) or not len(rows):
        return picture
    y, x = np.mgrid[0:h, 0:w]
    edge = (a > 0.05) & ~((x >= cols.min()) & (x <= cols.max()) & (y <= rows.max()))   # the interior's box, faded too
    if not edge.any():
        return picture
    ys, xs = np.nonzero(edge)
    top, bottom, left, right = ys.min(), ys.max(), xs.min(), xs.max()
    out = picture.copy()
    out[..., 3] *= ~((y > bottom) | ((y >= top) & ((x < left) | (x > right))))
    frame = panel.copy()
    frame[..., 3] *= edge
    return _over(frame, out)


def _over(top, bottom):
    a = top[..., 3:4] + bottom[..., 3:4] * (1.0 - top[..., 3:4])
    rgb = top[..., :3] * top[..., 3:4] + bottom[..., :3] * bottom[..., 3:4] * (1.0 - top[..., 3:4])
    return np.concatenate([np.where(a > 1e-4, rgb / np.maximum(a, 1e-4), 0.0), a], -1)


def mirrored(a, b):
    """Whether picture b is rather a mirror image of a than a copy."""
    if a.shape != b.shape:
        return False
    return np.abs(a[:, ::-1] - b).mean() < np.abs(a - b).mean()


# ------------------------------------------------------------------------------------------------ names

# The fighters' names as the select screen's name pictures spell them, by the code of their labels: the added
# fighter's name is put together from letters cut out of these pictures (the title's own lettering: silver
# letters with a soft black shadow). The frames' labels (`p1_chara_waku_<code>`) end on the fighter's name.
NAME_TEXTS = {
    'ali': 'ALISA', 'amk': 'ARMOR KING', 'ann': 'ANNA', 'ask': 'ASUKA', 'bae': 'BAEK', 'bob': 'BOB', 'bru': 'BRUCE',
    'bry': 'BRYAN', 'chr': 'CHRISTIE', 'dra': 'DRAGUNOV', 'dvj': 'DEVIL JIN', 'edd': 'EDDY', 'fen': 'FENG',
    'gan': 'GANRYU', 'hei': 'HEIHACHI', 'hwo': 'HWOARANG', 'jac': 'JACK-6', 'jc': 'JAYCEE', 'jin': 'JIN', 'jun': 'JUN',
    'kaz': 'KAZUYA', 'kin': 'KING', 'kum': 'KUMA', 'lar': 'LARS', 'law': 'MARSHALL LAW', 'lee': 'LEE', 'lei': 'LEI',
    'leo': 'LEO', 'lil': 'LILI', 'mar': 'MARDUK', 'mig': 'MIGUEL', 'mok': 'MOKUJIN', 'nin': 'NINA', 'ogr': 'OGRE',
    'pan': 'PANDA', 'pau': 'PAUL', 'rav': 'RAVEN', 'rog': 'ROGER Jr.', 'ste': 'STEVE', 'wan': 'WANG', 'xia': 'XIAOYU',
    'yos': 'YOSHIMITSU', 'jnp': 'JINPACHI', 'knm': 'KUNIMITSU', 'sli': 'SLIM BOB', 'flw': 'FOREST LAW',
    'mih': 'MIHARU', 'cbt': 'COMBOT', 'ang': 'ANGEL', 'mic': 'MICHELLE', 'pja': 'P.JACK', 'alx': 'ALEX',
    'gre': 'ANCIENT OGRE', 'vio': 'VIOLET', 'bcv': 'DR. BOSCONOVITCH', 'seb': 'SEBASTIAN', 'tig': 'TIGER',
}
NAME_LABEL = re.compile(r'^p1_chara_waku_([a-z]+)$')
OPAQUE = 0.95          # the letters' pixels are opaque, their shadow's are not
BRIGHT = 0.35          # a letter's column has pixels at least this bright (colour times alpha)
SHADOW = 12            # how far (pixels) the shadow is measured


def _distances(mask, limit):
    """Per pixel, the distance to the nearest pixel of `mask` (inf beyond `limit`)."""
    h, w = mask.shape
    out = np.full(mask.shape, np.inf)
    offsets = sorted(((dx * dx + dy * dy) ** 0.5, dx, dy) for dx in range(-limit, limit + 1)
                     for dy in range(-limit, limit + 1) if dx * dx + dy * dy <= limit * limit)
    for d, dx, dy in offsets:
        shifted = np.zeros_like(mask)
        shifted[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = \
            mask[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)]
        out = np.where(shifted & (out > d), d, out)
    return out


class Letters:
    """The title's lettering for names, learnt from the fighters' name pictures: each letter cut out (between the
    middles of the gaps around it), the gap between letters, a space's width and the shadow (colour and alpha by
    distance from the letters)."""

    def __init__(self):
        self.glyphs = {}               # letter: [(cut from a name with touching letters, letter's offset, width, cut)]
        self.gaps, self.spaces, self.margins = [], [], []
        self.ring_sum = np.zeros((SHADOW + 1, 4))
        self.ring_count = np.zeros(SHADOW + 1)

    def learn(self, text, pic):
        """Cuts the letters of name picture `pic` (h, w, 4 floats) that spells `text`."""
        chars = [c for c in text if c != ' ']
        bright = ((pic[..., :3].mean(-1) * pic[..., 3]) > BRIGHT).sum(0)
        runs, start = [], None
        for x, v in enumerate(list(bright >= 2) + [False]):
            if v and start is None:
                start = x
            if not v and start is not None:
                runs.append([start, x])
                start = None
        touching = False
        while 0 < len(runs) < len(chars):      # letters that touch (YA, WA): split the widest at its faintest column
            i = max(range(len(runs)), key=lambda k: runs[k][1] - runs[k][0])
            a, b = runs[i]
            lo, hi = a + (b - a) // 5, b - (b - a) // 5
            if hi <= lo:
                return
            x = lo + int(np.argmin(bright[lo:hi]))
            runs[i:i + 1] = [[a, x], [x, b]]
            touching = True
        if not runs or len(runs) != len(chars):
            return
        ink = np.nonzero(pic[..., 3].max(0) > 0.02)[0]
        cuts = [int(ink[0])] + [(runs[i][1] + runs[i + 1][0]) // 2 for i in range(len(runs) - 1)] + [int(ink[-1]) + 1]
        for i, ch in enumerate(chars):
            self.glyphs.setdefault(ch, []).append((touching, runs[i][0] - cuts[i], runs[i][1] - runs[i][0],
                                                   pic[:, cuts[i]:cuts[i + 1]].copy()))
        spaces, at = set(), 0
        for word in text.split(' ')[:-1]:
            at += len(word)
            spaces.add(at)                     # a space between letters at - 1 and at
        for i in range(1, len(runs)):
            if i in spaces:
                self.spaces.append(runs[i][0] - runs[i - 1][1])
            elif not touching:
                self.gaps.append(runs[i][0] - runs[i - 1][1])
        solid = pic[..., 3] > OPAQUE
        if solid.any():
            cols = np.nonzero(solid.any(0))[0]
            self.margins.append((int(cols[0]), pic.shape[1] - 1 - int(cols[-1])))
            d = _distances(solid, SHADOW)
            ring = np.where(solid | ~np.isfinite(d), 0, np.round(np.where(np.isfinite(d), d, 0))).astype(np.int64)
            ok = (ring <= SHADOW) & (ring >= 1)
            np.add.at(self.ring_sum, ring[ok], np.concatenate([pic[..., :3] * pic[..., 3:], pic[..., 3:]], -1)[ok])
            np.add.at(self.ring_count, ring[ok], 1)

    def glyph(self, ch):
        found = self.glyphs.get(ch)
        if not found:
            return None
        clean = [g for g in found if not g[0]] or found
        return sorted(clean, key=lambda g: g[2])[len(clean) // 2]       # the one of middle width

    def picture(self, text):
        """`text` in the title's lettering (h, w, 4 floats), or None when a letter of it is missing."""
        if not self.glyphs or not self.gaps:
            return None
        parts = [None if c == ' ' else self.glyph(c) for c in text]
        if any(p is None for c, p in zip(text, parts) if c != ' '):
            return None
        gap = int(np.median(self.gaps))
        space = int(np.median(self.spaces)) if self.spaces else 4 * gap
        left, right = (int(np.median([m[k] for m in self.margins])) for k in (0, 1))
        h = parts[[c != ' ' for c in text].index(True)][3].shape[0]
        x, placed = left, []
        for c, p in zip(text, parts):
            if p is None:
                x += space - gap
                continue
            _, offset, width, cut = p
            placed.append((x - offset, cut))
            x += width + gap
        w = x - gap + right
        pad = SHADOW
        letters = np.zeros((h, w + 2 * pad, 4), np.float32)
        for x0, cut in placed:
            x0 += pad
            solid = cut[..., 3:] > OPAQUE
            area = letters[:, x0:x0 + cut.shape[1]]
            area[:] = np.where(solid, cut, area)
        letters = letters[:, pad:pad + w]
        solid = letters[..., 3] > OPAQUE
        # the shadow, by distance from the letters, as measured on the title's names
        d = np.round(_distances(solid, SHADOW))
        n = np.maximum(self.ring_count, 1)[:, None]
        mean = self.ring_sum / n
        out = letters.copy()
        for k in range(1, SHADOW + 1):
            at = (d == k) & ~solid
            alpha = mean[k, 3]
            if alpha > 0:
                out[at] = np.concatenate([mean[k, :3] / alpha, [alpha]])
        return out

    @classmethod
    def of_layout(cls, layout):
        """The letters of a layout's name pictures (None when it has none)."""
        lm = layout.lm
        letters = cls()
        for sprite in lm.sprites():
            labels = lm.labels_of(sprite)
            for name in labels:
                m = NAME_LABEL.match(name)
                if not m or m.group(1) not in NAME_TEXTS:
                    continue
                frame = layout.label_frame(sprite, labels, name, True)
                for c in (frame.children if frame else []):
                    shape = lm.char(c.char) if isinstance(c, lmb.Place) and c.mode != lmb.MODE_MOVE else None
                    if isinstance(shape, lmb.Shape) and shape.graphics and shape.graphics[0].atlas in layout.atlases:
                        letters.learn(NAME_TEXTS[m.group(1)], layout.shape_picture(shape)[0])
            if letters.glyphs:
                return letters
        return None


# ------------------------------------------------------------------------------------------------ layouts

def code_label(label, code):
    """`label` with Paul's code token replaced: face_pau_lose -> face_<code>_lose (None if it has none)."""
    m = re.search(r'(?:^|(?<=_))%s(?=_|$)' % PAUL, label)
    return None if m is None else label[:m.start()] + code + label[m.end():]


class Layout:
    """One LMB layout and its texture container, with the fighter's labels and pictures added."""

    def __init__(self, lm, textures, sources, code, codes, cell=None):
        self.lm, self.textures, self.sources, self.code, self.codes = lm, textures, sources, code, codes
        self.cell = cell              # the new grid cell: {anchor, columns, grid_row} (add_cell)
        self.atlases = {t['gidx']: t for t in textures['textures']}
        self.decoded = {}
        self.new = []                  # (shape id, Paul's shape, picture): pictures waiting for a page
        self.replace = []              # (shape, shape id): the shape gets that one's graphics once it has its page
        self.changed = False

    # -- the title's pictures
    def atlas(self, aid):
        if aid not in self.decoded:
            self.decoded[aid] = _float(nut.decode(self.atlases[aid]))
        return self.decoded[aid]

    def shape_picture(self, shape):
        """A shape's picture (its first graphic's region of its atlas), and the region's size in texels."""
        g = shape.graphics[0]
        a = self.atlas(g.atlas)
        h, w = a.shape[:2]
        u0, v0, u1, v1 = g.uv_box()
        x0, y0, x1, y1 = round(u0 * w), round(v0 * h), round(u1 * w), round(v1 * h)
        return a[y0:y1, x0:x1], (x1 - x0, y1 - y0)

    def label_frame(self, sprite, labels, name, last):
        """What label `name` shows: its keyframe (the display list at the label), or with `last` its last frame
        when the label plays on (None when it does not)."""
        if not last:
            return sprite.frame(labels[name], True)
        start, end = self.lm.label_span(sprite, name)
        return sprite.frame(end - 1) if end - start > 1 else None

    def fighters_pictures(self, sprite, labels, prefix, suffix, depth, size, last=False):
        """Every fighter's picture at `depth` of its label (prefix + code + suffix), resized to `size`."""
        out = []
        for code in self.codes:
            name = prefix + code + suffix
            if name not in labels:
                continue
            key = self.label_frame(sprite, labels, name, last)
            hits = [c for c in (key.children if key else []) if isinstance(c, lmb.Place) and c.depth == depth
                    and c.mode != lmb.MODE_MOVE]
            shape = self.lm.char(hits[0].char) if hits else None
            if not isinstance(shape, lmb.Shape) or not shape.graphics or shape.graphics[0].atlas not in self.atlases:
                continue
            pic, _ = self.shape_picture(shape)
            if pic.size:
                out.append(pic if pic.shape[1::-1] == size else _resize(pic, *size))
        return np.stack(out) if out else None

    # -- the fighter's labels
    def add_labels(self):
        lm = self.lm
        for sprite in lm.sprites():
            labels = lm.labels_of(sprite)
            for paul in [n for n in labels if code_label(n, self.code)]:
                new = code_label(paul, self.code)
                if new in labels:
                    continue
                prefix, suffix = paul.split(PAUL, 1) if paul.startswith(PAUL) else re.split(
                    r'(?<=_)%s(?=_|$)' % PAUL, paul, maxsplit=1)
                char_map = self.own_shapes(sprite, labels, paul, prefix, suffix)
                lm.add_label_like(sprite, paul, new, char_map)
                self.changed = True

    def own_shapes(self, sprite, labels, paul, prefix, suffix):
        """{Paul's shape: the fighter's new shape} for each depth where the fighters' shapes differ, in what the
        label shows at once and, when it plays on, at its end (the frames' labels end on the fighter's name)."""
        lm = self.lm
        names = [prefix + c + suffix for c in self.codes if c != PAUL and prefix + c + suffix in labels]
        char_map = {}
        for last in (False, True):
            mine = self.label_frame(sprite, labels, paul, last)
            if mine is None or (GAME_DRAWN.match(prefix) and not last):
                continue                                    # the game draws the frames' portraits itself
            others = [self.label_frame(sprite, labels, n, last) for n in names]
            for c in mine.children:
                shape = lm.char(c.char) if isinstance(c, lmb.Place) and c.mode != lmb.MODE_MOVE else None
                if not isinstance(shape, lmb.Shape) or shape.id in char_map:
                    continue
                theirs = [[x.char for x in o.children if isinstance(x, lmb.Place) and x.depth == c.depth
                           and x.mode != lmb.MODE_MOVE] for o in others if o]
                if theirs and all(t == [shape.id] for t in theirs):
                    continue                                # every fighter shows this one: a frame, a background
                if not shape.graphics or shape.graphics[0].atlas not in self.atlases:
                    continue
                pic, size = self.shape_picture(shape)
                if not min(size):
                    continue
                if 'name' in prefix or (last and GAME_DRAWN.match(prefix)):
                    char_map[shape.id] = self.new_shape(shape, self.sources.title_name(*size))
                    continue
                stack = self.fighters_pictures(sprite, labels, prefix, suffix, c.depth, size, last)
                mirror = False
                if 'p2' in prefix:                          # player 2's pictures: mirrored if player 1's are
                    one = prefix.replace('p2', 'p1')
                    if one + PAUL + suffix in labels:
                        ref = self.fighters_pictures(sprite, labels, one, suffix, c.depth, size, last)
                        mirror = ref is not None and mirrored(ref[0], pic)
                mine_pic = self.sources.framed(face_place(*size), size[0], size[1], mirror)
                picture = compose(stack, mine_pic) if stack is not None and len(stack) >= 3 else mine_pic
                char_map[shape.id] = self.new_shape(shape, picture)
        return char_map

    def new_shape(self, like, picture):
        """A shape like `like` (same geometry; as wide as `picture` needs, about the same centre: names) that will
        show `picture` (placed on a page in pages())."""
        _, (w, _) = self.shape_picture(like)
        scale = picture.shape[1] / w if w else 1.0
        if abs(scale - 1.0) > 1e-6:
            x0, _, x1, _ = like.graphics[0].xy_box()
            cx = (x0 + x1) / 2
            graphics = [lmb.Graphic(g.atlas, [[cx + (x - cx) * scale, y, u, v] for x, y, u, v in g.verts],
                                    list(g.indices), g.fill) for g in like.graphics]
            like = lmb.Shape(like.id, like.bounds, graphics, like.unk1, like.unk3)
        cid = self.lm.take_id()
        self.new.append((cid, like, picture))
        # placeholder: the real graphics come in pages(); reserve the id now
        self.lm.add_shape(cid, [lmb.Graphic(like.graphics[0].atlas, [list(v) for v in like.graphics[0].verts],
                                            list(like.graphics[0].indices), like.graphics[0].fill)])
        return cid

    # -- the select grid's new cell
    def add_cell(self):
        lm = self.lm
        below = lm.find_named('face_panel_' + self.cell['anchor'])
        beside = lm.find_named('face_panel_' + GRID_BESIDE)
        pitch = [lm.find_named('face_panel_' + c) for c in PITCH_FROM]
        if not below or not beside or not all(pitch) or lm.find_named('face_panel_' + self.code):
            return
        grid, _, place = below[0]
        panel = lm.char(place.char)
        other = lm.char(beside[0][2].char)
        if not isinstance(panel, lmb.Sprite) or not isinstance(other, lmb.Sprite):
            return
        # the panel's own picture: the shapes it shows that the neighbour's panel does not
        theirs = {c.char for _, c in other.all_children() if isinstance(c, lmb.Place)}
        empty = [lm.char(c.char) for _, c in panel.all_children() if isinstance(c, lmb.Place) and c.char in theirs
                 and isinstance(lm.char(c.char), lmb.Shape)]
        char_map = {}
        stack = self.panel_pictures()
        for _, c in panel.all_children():
            shape = lm.char(c.char) if isinstance(c, lmb.Place) else None
            if isinstance(shape, lmb.Shape) and shape.id not in theirs and shape.id not in char_map:
                pic, size = self.shape_picture(shape)
                mine = self.sources.framed(face_place(*size), size[0], size[1])
                ok = stack is not None and stack.shape[1:3] == (size[1], size[0])
                mine = compose(stack, mine) if ok else mine
                if empty:
                    frame, fsize = self.shape_picture(empty[0])
                    if fsize == size:
                        mine = in_frame(mine, frame)
                char_map[shape.id] = self.new_shape(shape, mine)
        sid = lm.take_id(below=grid.id, above=max(panel.id, max(char_map.values())))
        lm.clone_sprite(panel.id, sid, char_map)
        # in the grid: everything the panel below does, at a new depth after the panels, in the top row
        panels = [c.depth for _, c in grid.all_children() if isinstance(c, lmb.Place) and c.mode == lmb.MODE_PLACE
                  and c.name and lm.symbols[c.name].startswith('face_panel_')]
        depth = max(panels) + 1
        lm.insert_depth(grid, depth)
        xs = [lm.matrices[p[0][2].posid][4] if p[0][2].posflags == lmb.POS_MATRIX else None for p in pitch]
        top = lm.matrices[beside[0][2].posid][5] if beside[0][2].posflags == lmb.POS_MATRIX else None
        if top is None or None in xs:
            return
        dx = (xs[1] - xs[0]) * self.cell['columns']
        in_top = self.cell['grid_row'] == 0

        def to_cell(m):
            m[4] += dx
            if in_top:
                m[5] = top
            return m

        def to_cell_position(p):
            p[0] += dx
            if in_top:
                p[1] = top
            return p
        lm.clone_depth(grid, place.depth, depth, char=sid, name='face_panel_' + self.code,
                       matrix_fn=to_cell, position_fn=to_cell_position)
        if in_top:
            x = lm.matrices[place.posid][4] + dx if place.posflags == lmb.POS_MATRIX else None
            boxes = [lm.char(c.char).graphics[0].xy_box() for c in panel.frames[0].children
                     if isinstance(c, lmb.Place) and isinstance(lm.char(c.char), lmb.Shape)]
            if x is not None and boxes:
                self.fit_spacer(x + min(b[0] for b in boxes), x + max(b[2] for b in boxes), xs[1] - xs[0])
        self.changed = True

    def fit_spacer(self, x0, x1, pitch):
        """The grid's empty top-row corners are covered by a grille (sprites `spacer_left` / `spacer_right`, one shape
        per grid width). The right one whose edge falls in the new cell (x0..x1, in the grid) still covers it:
        it becomes the left one whose edge, mirrored, falls there too (the grid is symmetric), so the grille stops
        at the new cell as the left one stops at the first top-row cell, and the background shows behind it. In a
        grille already fitted so (a second new cell, right of the first) it is shortened by a column (pitch)."""
        lm = self.lm
        sides = [lm.find_named('spacer_' + s) for s in ('right', 'left')]
        if not all(sides):
            return
        (_, _, right), (_, _, left) = sides[0][0], sides[1][0]

        def origin(p):
            if p.posflags == lmb.POS_MATRIX:
                return lm.matrices[p.posid][4]
            return lm.positions[p.posid][0] if p.posflags == lmb.POS_POSITION else 0.0

        def shapes(p):
            sprite = lm.char(p.char)
            ids = {c.char for _, c in sprite.all_children() if isinstance(c, lmb.Place) and c.mode != lmb.MODE_MOVE}
            return [lm.char(i) for i in sorted(ids) if isinstance(lm.char(i), lmb.Shape)]
        rx = origin(right)
        mine = [s for s in shapes(right) if x0 <= rx + s.graphics[0].xy_box()[0] <= x1]
        theirs = [s for s in shapes(left) if x0 <= rx - s.graphics[0].xy_box()[2] <= x1]
        if len(mine) == 1 and getattr(mine[0], 'fitted', False):
            self.shorten_spacer(mine[0], pitch)        # one more cell: one column (as far as the last one)
            return
        if len(mine) != 1 or len(theirs) != 1 or len(theirs[0].graphics) != 1:
            return
        g, like = mine[0].graphics[0], theirs[0].graphics[0]
        _, y0, _, y1 = g.xy_box()
        _, ly0, _, ly1 = like.xy_box()
        # mirrored in x (so the triangles turn the other way: their indices reversed), its height the right one's
        verts = [[-x, y0 + (y - ly0) * (y1 - y0) / (ly1 - ly0), u, v] for x, y, u, v in like.verts]
        indices = [i for t in range(0, len(like.indices), 3) for i in reversed(like.indices[t:t + 3])]
        mine[0].graphics = [lmb.Graphic(like.atlas, verts, indices, like.fill)]
        mine[0].bounds = lm.add_record(lmb.T_BOUNDS, mine[0].graphics[0].xy_box())
        mine[0].fitted = True              # the next new cell in it (fit_spacer) shortens it

    def shorten_spacer(self, shape, cut):
        """The fitted right grille (fit_spacer) with its top band `cut` units shorter at its open end, which a new cell
        took: its inner edge (the bevelled border, SPACER_EDGE texels) is kept, and texels of the band's perforation
        are cut out (cut_columns); the band's lower part (beside the lower rows, at the far end) stays where it is.
        A new picture on a page of the layout's (pages())."""
        g = shape.graphics[0]
        pic, (w, h) = self.shape_picture(shape)
        x0, _, x1, _ = g.xy_box()
        k = round(cut * w / (x1 - x0))              # texels to cut (1 unit = 1 texel in the title's grilles)
        # the picture is in texel order; the grille's open end is the texture's high-u end when the shape is
        # mirrored (its x runs against u), else the low-u one
        u_at_x0 = min(g.verts, key=lambda v: v[0])[2]
        edge_high = u_at_x0 >= max(v[2] for v in g.verts) - 1e-6
        if not 0 < k < w - 2 * SPACER_EDGE:
            return
        new = cut_columns(pic, k, edge_high)
        # the same quad, its open end moved in by `cut`
        moved = [[x + cut * (x1 - x) / (x1 - x0), y, u, v] for x, y, u, v in g.verts]
        like = lmb.Shape(shape.id, shape.bounds, [lmb.Graphic(g.atlas, moved, list(g.indices), g.fill)],
                         shape.unk1, shape.unk3)
        cid = self.lm.take_id()
        self.new.append((cid, like, new))
        self.lm.add_shape(cid, [lmb.Graphic(g.atlas, [list(v) for v in moved], list(g.indices), g.fill)])
        self.replace.append((shape, cid))
        self.changed = True

    def panel_pictures(self):
        """Every fighter's grid panel picture (the shape its panel shows and the next fighter's does not)."""
        lm = self.lm
        sprites = []
        for code in self.codes:
            hit = lm.find_named('face_panel_' + code)
            if hit and isinstance(lm.char(hit[0][2].char), lmb.Sprite):
                sprites.append(lm.char(hit[0][2].char))
        shapes = []
        for i, sp in enumerate(sprites):
            nxt = sprites[(i + 1) % len(sprites)]
            theirs = {c.char for _, c in nxt.all_children() if isinstance(c, lmb.Place)}
            own = [lm.char(c.char) for _, c in sp.all_children() if isinstance(c, lmb.Place)
                   and isinstance(lm.char(c.char), lmb.Shape) and c.char not in theirs]
            if own:
                shapes.append(own[0])
        if len(shapes) < 3:
            return None
        pics = [self.shape_picture(s) for s in shapes]
        size = max(set(p[1] for p in pics), key=[p[1] for p in pics].count)
        return np.stack([p[0] for p in pics if p[1] == size])

    # -- texture pages
    def pages(self):
        """Puts the new pictures on new texture pages; returns the pages' textures."""
        if not self.new:
            return []
        items = sorted(self.new, key=lambda n: -n[2].shape[0])
        placed, x, y, row, width = [], 0, 0, 0, 0
        for cid, like, pic in items:
            h, w = pic.shape[:2]
            if x + w > PAGE_WIDTH:
                x, y, row = 0, y + row + 4, 0
            placed.append((cid, like, pic, x, y))
            x += w + 4
            row = max(row, h)
            width = max(width, x)
        pw, ph = (width + 3) & ~3, (y + row + 3) & ~3
        page = np.zeros((ph, pw, 4), np.float32)
        aid = self.lm.add_atlas(pw, ph)
        for cid, like, pic, px, py in placed:
            h, w = pic.shape[:2]
            page[py:py + h, px:px + w] = pic
            shape = self.lm.char(cid)
            shape.graphics = [self.remap(g, like.graphics[0], (px / pw, py / ph, (px + w) / pw, (py + h) / ph))
                              for g in like.graphics]
        for target, cid in self.replace:
            target.graphics = self.lm.char(cid).graphics
            target.bounds = self.lm.add_record(lmb.T_BOUNDS, target.graphics[0].xy_box())
        tex = nut.make_texture(_uint8(page), aid, fmt=2, mips=1)
        return [tex]

    @staticmethod
    def remap(g, first, box):
        """A copy of graphic g with its texture coordinates moved from `first`'s region to `box` on a new page."""
        u0, v0, u1, v1 = first.uv_box()
        nu0, nv0, nu1, nv1 = box
        verts = []
        for x, y, u, v in g.verts:
            su = (u - u0) / (u1 - u0) if u1 > u0 else 0.0
            sv = (v - v0) / (v1 - v0) if v1 > v0 else 0.0
            verts.append([x, y, nu0 + su * (nu1 - nu0), nv0 + sv * (nv1 - nv0)])
        return lmb.Graphic(None, verts, list(g.indices), g.fill)
