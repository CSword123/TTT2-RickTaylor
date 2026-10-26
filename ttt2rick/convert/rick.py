"""Rick -> a TTT2 fighter's body files under a donor's names (first: Marduk, `mar`), for the update overlay.

python -m ttt2rick.convert.rick <game folder> <rick export dir, e.g. work/rick/brawler> <rick textures dir> <out dir>

1. Repose: Rick's bind pose is an A-pose; TTT2's is the donor's T-pose, and the donor's bones keep their rest
   rotations (the game drives bones by index with the donor's animations), so each of Rick's limb joints is turned
   until its segment points the way the donor's matching segment does (AIM), and the mesh follows by its skin.
2. Skeleton: the donor's, its joints moved to Rick's (Petexy's skeleton.build, by the Tekken 7 names in ANCHOR).
3. Skin: each Rick joint's weights go to one TTT2 bone (WEIGHTS), four per vertex.
4. Model: one NUD mesh per Rick mesh; materials are copies of a template (TEMPLATES: the donor's skin for skin, a
   costume part's cloth for the mask, clothes and shoes, the donor's face overlay for hair) with Rick's colour and
   normal maps and flat textures of the template's average for the other slots.
5. Item database: the donor's, body only (Petexy's itemdb.body_only), so none of its costume parts are drawn.
6. Blood: the jeans and shoes are cleaned of Splatterhouse's painted-in blood (ttt2rick.convert.clean);
   <code>_blood.nut is the same NUT with it (recomp/runtime/rick_slot.cpp loads it under TTT2_RICK_BLOOD=1).
Writes files/<code>.nud/.nut/_blood.nut/.bon/.xml (install that folder with ttt2rick.ttt2.overlay) and preview.png.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

from . import clean as blood
from ..splatterhouse.preview import render
from ..ttt2 import xbox
from ..ttt2.archive import Archives
from ..ttt2.extract import VIEWS
from ..ttt2.petexy import bone, itemdb, nud, nut, skeleton, strips

DONOR = 'mar'
GIDX_FIRST = 0x1040F000         # above the game's own texture ids (0x10404fac at most)
MAX_TEX = 512                   # longest side (the game's fighters: 512)
MIPS = 3                        # longer chains make the game bind garbage (Petexy)
TEXTURE_BUDGET = 4 << 20        # bytes; the game's fighters have 3.4-4.7 MB
HEAD_MESHES = {'rick_head_geo', 'rick_neck', 'l_eye', 'r_eye', 'alpha_hair'}
OVERLAY_MESHES = {'alpha_hair'}
GLOW_MESHES = {'l_eye', 'r_eye'}        # unlit: the eyes behind the mask glow yellow
GLOW_GAIN = 1.6                         # the iris's brightness on the unlit material
GLOW_DARK = 0.15                        # the rest of the eyeball: a shadowed socket, so only the iris shows
GLOW_SHRINK = 0.6                       # the glowing iris, as a share of the texture's iris size
GLOW_YELLOW = np.array([255, 230, 60], np.float32)     # the iris at least this bright
SKIN_TEXTURE = 'rick_body_base.dds'     # meshes coloured by it get the skin material, the others cloth
# Splatterhouse's colour maps have their creases' shading painted in, and TTT2's lighting darkens them again: in game
# Rick's skin came out at 0.67 of Marduk's brightness and redder. His skin-coloured pixels (skin_weight) are graded
# by the ratio of Marduk's skin colour to his (medians, per channel), in the textures of his skin and head meshes;
# blood, the mask and cloth keep theirs. Graded only that far he still rendered at 0.81 of Marduk and a little redder
# (the same with a flat normal map, so it is the colour, which every stage's light multiplies): RENDER_TRIM scales
# the target further, measured in game (2026-10-23). It stays close to uniform: the game's skin shading reddens
# every skin a lot (Marduk renders at G/R 0.57 from a texture at 0.76), and the user's picture of Rick has Marduk's
# texture hue (G/R 0.75, B/R 0.61), so a target with another hue (tried: matching the picture in the rendered
# image) turns him grey.
RENDER_TRIM = np.array([1.20, 1.25, 1.30])
# The neck shares the mask's texture, whose skin starts from another tone: every texture's skin is graded to the
# same colour (the body's, graded; TextureBank skin_target), and the neck gets the skin material like the body.
# Graded to the body's median alone, the neck came out 20-33% lighter and greyer than the body where they meet (the
# body is darker and redder there than its median; the mask's skin is even): in game its upper half looked flat and
# light over a darker wedge of the body. So the mask's skin is graded on to the body's colour at the seam
# (seam_scale: the vertices the two meshes share).
SKIN_MESHES = {'rick_neck'}
# The wallet chain's loop at the front of the jeans (Splatterhouse binds it to the root only) is half inside the jeans
# in his bind pose (48 of its 117 vertices behind their front, up to 15 mm): those come out in front of them by
# CHAIN_GAP mm, or TTT2 hides most of it.
CHAIN, CHAIN_COVER, CHAIN_GAP = 'brawlerBelt', 'brawlerDickies', 4.0
# Splatterhouse makes the chain silver with its gloss map, which the cloth material has no use for: its colour is the
# gloss map's x CHAIN_SHINE, in the base map's hue (dark grey on the dark jeans otherwise).
CHAIN_SHINE = 1.25
SKIN_SHARING = {'rick_head_geo'}         # its texture is the neck's: graded the same, so the two share it
MARDUK_SKIN = [0x10400B9D, 0x10400B97, 0x10400BA0]     # mar.nut: the arm, neck and leg skin colours
# material templates: kind -> (entry name or key, mesh, polygon); the cloth is a costume part of Jun's (her model pack,
# member 95), which Petexy's added fighters use too, with the NUTs holding its textures
TEMPLATES = {'skin': (DONOR + '.nud', 'ude_A_O_OBJ', 0), 'overlay': (DONOR + '.nud', 'cha:kao_O_OBJ', 3),
             'cloth': (0xD4F28D09, 'jun_upb_1p_b', 0),
             'glow': ('ogr.nud', 'MODEL_dummy', 0)}          # flags 0x21000001: one texture, no lighting
TEMPLATE_TEXTURES = [DONOR + '.nut', 'jun.nut', 0x24F8AE59, 0x277C7A37, 0xAD9B60F0, 0x900FD8C4, 'ogr.nut']

# Rick joint -> TTT2 bone its skin weights go to (TTT2 names without 'cha:'); like Petexy's t7_weight_target
WEIGHTS = {'root_jnt': 'KOSHI_jnt', 'C_lowerTorso_jnt': 'MUNE1_jnt', 'C_midTorso_jnt': 'MUNE2_jnt',
           'C_upperTorso_jnt': 'MUNE2_jnt', 'C_neck_01_jnt': 'KUBI_jnt_assist', 'C_neck_02_jnt': 'KUBI_jnt_assist',
           'C_head_01_jnt': 'ATAMA_jnt_assist'}
# Tekken 7 joint name (Petexy's skeleton.ANCHOR) -> the Rick joint whose position it takes
ANCHOR = {'BASE': 'C_lowerTorso_jnt', 'Hip': 'C_lowerTorso_jnt', 'Spine1': 'C_lowerTorso_jnt',
          'Spine2': 'C_midTorso_jnt', 'Neck': 'C_neck_01_jnt', 'Head': 'C_head_01_jnt'}
# Rick (joint, child) -> donor (bone, child bone) whose direction the segment takes in the T-pose
AIM = []
FINGERS = (('thumb', 'Thumb', 'OYA'), ('index', 'Index', 'HITO'), ('mid', 'Middle', 'NAKA'),
           ('ring', 'Ring', 'KUSU'), ('pinky', 'Pinky', 'KO'))
for s in 'LR':
    WEIGHTS.update({'%s_clavicle_01_jnt' % s: 'SAKOTSU_0_%s_jnt' % s, '%s_clavicle_02_jnt' % s: 'SAKOTSU_%s_jnt' % s,
                    '%s_shoulder_jnt' % s: 'KATA_0_%s_jnt' % s, '%s_deltoid_jnt' % s: 'KATA_50_%s' % s,
                    '%s_elbow_jnt' % s: 'UDE_%s_jnt' % s, '%s_forearm_jnt' % s: 'UDE_50_%s' % s,
                    '%s_wrist_jnt' % s: 'TE_%s_jnt' % s, '%s_weapon_jnt' % s: 'TE_%s_jnt' % s,
                    '%s_upperLeg_jnt' % s: 'MOMO_0_%s' % s, '%s_lowerLeg_jnt' % s: 'SUNE_%s' % s,
                    '%s_ankle_jnt' % s: 'ASHI_%s_jnt' % s, '%s_ballFoot_jnt' % s: 'TSUMASAKI_%s_jnt' % s})
    ANCHOR.update({'%s_Shoulder' % s: '%s_clavicle_02_jnt' % s, '%s_Arm' % s: '%s_shoulder_jnt' % s,
                   '%s_ForeArm' % s: '%s_elbow_jnt' % s, '%s_Hand' % s: '%s_wrist_jnt' % s,
                   '%s_UpLeg' % s: '%s_upperLeg_jnt' % s, '%s_Leg' % s: '%s_lowerLeg_jnt' % s,
                   '%s_Foot' % s: '%s_ankle_jnt' % s, '%s_Toe' % s: '%s_ballFoot_jnt' % s})
    AIM += [(('%s_shoulder_jnt' % s, '%s_elbow_jnt' % s), ('KATA_%s_jnt' % s, 'UDE_%s_jnt' % s)),
            (('%s_elbow_jnt' % s, '%s_wrist_jnt' % s), ('UDE_%s_jnt' % s, 'TE_%s_jnt' % s)),
            (('%s_wrist_jnt' % s, '%s_midFinger_01_jnt' % s), ('TE_%s_jnt' % s, 'NAKA3_%s' % s)),
            (('%s_upperLeg_jnt' % s, '%s_lowerLeg_jnt' % s), ('MOMO_%s_jnt' % s, 'HIZA_%s_jnt' % s)),
            (('%s_lowerLeg_jnt' % s, '%s_ankle_jnt' % s), ('HIZA_%s_jnt' % s, 'ASHI_%s_jnt' % s)),
            (('%s_ankle_jnt' % s, '%s_ballFoot_jnt' % s), ('ASHI_%s_jnt' % s, 'TSUMASAKI_%s_jnt' % s))]
    for rick, t7, ttt2 in FINGERS:
        for k in (1, 2, 3):                      # Rick _01 = proximal = TTT2 3 = Tekken 7 1
            WEIGHTS['%s_%sFinger_%02d_jnt' % (s, rick, k)] = '%s%d_%s' % (ttt2, 4 - k, s)
            ANCHOR['%s_%s%d' % (s, t7, k)] = '%s_%sFinger_%02d_jnt' % (s, rick, k)
        for k in (1, 2):
            AIM.append((('%s_%sFinger_%02d_jnt' % (s, rick, k), '%s_%sFinger_%02d_jnt' % (s, rick, k + 1)),
                        ('%s%d_%s' % (ttt2, 4 - k, s), '%s%d_%s' % (ttt2, 3 - k, s))))
# the wrist's roll: Rick's index -> pinky knuckles across the hand like the donor's
ROLL = {'%s_wrist_jnt' % s: (('%s_indexFinger_01_jnt' % s, '%s_pinkyFinger_01_jnt' % s),
                             ('HITO3_%s' % s, 'KO3_%s' % s)) for s in 'LR'}


def _unit(v):
    return v / max(np.linalg.norm(v), 1e-12)


def _rotation(a, b):
    """The smallest rotation taking direction a to direction b."""
    a, b = _unit(a), _unit(b)
    v, c = np.cross(a, b), float(a @ b)
    if np.linalg.norm(v) < 1e-9:
        if c > 0:
            return np.eye(3)
        p = _unit(np.cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0]))
        return 2 * np.outer(p, p) - np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def _about(p, R):
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = p - R @ p
    return M


def _apply(M, p):
    return M[:3, :3] @ p + M[:3, 3]


def repose(names, parents, P, donor_pos):
    """Per-joint world deltas (n, 4, 4) taking Rick's bind pose to the donor's limb directions."""
    idx = {n: i for i, n in enumerate(names)}
    aim = {idx[j]: (idx[c], donor_pos[b] - donor_pos[a]) for (j, c), (a, b) in AIM}
    roll = {idx[j]: (idx[x], idx[y], donor_pos[b] - donor_pos[a]) for j, ((x, y), (a, b)) in ROLL.items()}
    D = np.zeros((len(names), 4, 4))
    for j in range(len(names)):
        if parents[j] >= j:
            raise ValueError('Rick\'s skeleton lists %s before its parent' % names[j])
        D[j] = D[parents[j]] if parents[j] >= 0 else np.eye(4)
        if j in aim:
            c, target = aim[j]
            p = _apply(D[j], P[j])
            D[j] = _about(p, _rotation(_apply(D[j], P[c]) - p, target)) @ D[j]
            if j in roll:
                x, y, want = roll[j]
                axis = _unit(target)
                have = _apply(D[j], P[y]) - _apply(D[j], P[x])
                have, want = have - axis * (have @ axis), want - axis * (want @ axis)
                D[j] = _about(p, _rotation(have, want)) @ D[j]
    return D


def reposed(names, parents, P, donor_pos, info, data):
    """repose's deltas, then lifted: straightened legs reach lower than the bent ones did, so the soles are stood on
    the floor (y = 0) again. These take Rick's bind mesh to the TTT2 one (ttt2rick.convert.idle undoes them)."""
    D = repose(names, parents, P, donor_pos)
    floor = min(skin(D, data['mesh%d_positions' % k].astype(np.float64), data['mesh%d_normals' % k].astype(
        np.float64), data['mesh%d_joints' % k], data['mesh%d_weights' % k].astype(np.float64))[0][:, 1].min()
        for k in range(len(info['meshes'])))
    lift = np.eye(4)
    lift[1, 3] = -floor
    return lift @ D


def foot_heights(skel, names, P):
    """The skeleton's parameters 1-4: the ankles' and toes' heights over the soles (L, R, L, R), in units the game
    multiplies by the skeleton's scale. Every title skeleton has its ASHI / TSUMASAKI joints at about these times its
    scale (some a few mm lower: shoe soles), so they are where the game puts the feet on the floor. They are taken
    with his feet flat, in his own bind pose (P, soles at y = 0), as his stance and guard keep them
    (ttt2rick.convert.idle): the T-pose's feet are aimed down like the donor's, which lifts the ankles off the floor."""
    params = list(skel['params'])
    for k, j in enumerate(('L_ankle_jnt', 'R_ankle_jnt', 'L_ballFoot_jnt', 'R_ballFoot_jnt')):
        params[1 + k] = round(float(P[names.index(j)][1] / skel['scale']), 1)
    skel['params'] = params


def skin(D, positions, normals, joints, weights):
    M = np.einsum('vk,vkij->vij', weights, D[joints])
    p = np.einsum('vij,vj->vi', M[:, :3, :3], positions) + M[:, :3, 3]
    n = np.einsum('vij,vj->vi', M[:, :3, :3], normals)
    return p, n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def pow2(w, h, cap=MAX_TEX):
    def p2(x):
        return 1 << max(2, int(round(np.log2(max(4, x)))))
    s = min(1.0, cap / max(w, h))
    return min(cap, p2(w * s)), min(cap, p2(h * s))


def skin_weight(rgb):
    """0..1 per pixel: how much a pixel is skin (warm, r > g > b, green 55-95% of red, not too dark)."""
    r, g, b = (rgb[..., i].astype(np.float32) for i in range(3))
    ratio = g / np.maximum(r, 1.0)
    w = np.clip((ratio - 0.50) / 0.08, 0, 1) * np.clip((0.97 - ratio) / 0.05, 0, 1)
    w *= np.clip((r - 45.0) / 25.0, 0, 1) * ((r >= g) & (g >= b))
    return w


def skin_median(rgb):
    return np.median(rgb.reshape(-1, rgb.shape[-1])[skin_weight(rgb).reshape(-1) > 0.5][:, :3], 0)


class TextureBank:
    def __init__(self, skin_target=None):
        self.images, self.fmts, self.keys = [], [], {}
        self.skin_target = skin_target        # RGB the skin of colour(..., skin=True) is graded to (its median)
        self.skin_scale = {}                  # path -> RGB factor on that texture's graded skin (seam_scale)
        self.bloody = {}                      # image index -> the image with Splatterhouse's blood (convert.clean)

    def add(self, key, rgba, fmt):
        if key not in self.keys:
            self.keys[key] = GIDX_FIRST + len(self.images)
            self.images.append(np.asarray(rgba, np.uint8))
            self.fmts.append(fmt)
        return self.keys[key]

    def colour(self, path, alpha, skin=False):
        im = Image.open(path).convert('RGBA')
        size = pow2(*im.size)
        ramp = blood.CLEAN.get(os.path.basename(path))
        a = np.array(im.resize(size, Image.LANCZOS))
        if not alpha:
            a[..., 3] = 255
        if ramp:                                       # the clothes' blood off (at the texture's own size), the
            bloody = a.copy()                          # original kept for the bloody variant (textures(bloody=True))
            a = np.array(Image.fromarray(blood.clean(np.asarray(im), ramp)).resize(size, Image.LANCZOS))
            if not alpha:
                a[..., 3] = 255
        if skin and self.skin_target is not None:      # a few passes: grading changes which pixels count as skin
            src = a[..., :3].astype(np.float32)
            w = skin_weight(a)[..., None]
            gain = self.skin_target / skin_median(a)
            for _ in range(4):
                a[..., :3] = np.clip(src * (1 + w * (gain - 1)), 0, 255).astype(np.uint8)
                gain = gain * self.skin_target / skin_median(a)
            if path in self.skin_scale:              # then on to the body's colour at a seam: saturated skin only,
                r, b = src[..., 0], src[..., 2]       # as the mask's warm bone white counts as skin too (sat < 0.4)
                ws = w * np.clip(((r - b) / np.maximum(r, 1.0) - 0.35) / 0.08, 0, 1)[..., None]
                a[..., :3] = np.clip(a[..., :3] * (1 + ws * (self.skin_scale[path] - 1)), 0, 255).astype(np.uint8)
        gidx = self.add(('img', path, alpha, skin), a, 2 if alpha else 0)
        if ramp:
            self.bloody[gidx - GIDX_FIRST] = bloody
        return gidx

    def normal(self, path):
        """RGB normal map (R = X, G = Y) -> TTT2's BC3 layout (A = X, G = Y flipped), as Petexy does."""
        im = Image.open(path).convert('RGB')
        a = np.array(im.resize(pow2(*im.size), Image.LANCZOS))
        out = np.zeros(a.shape[:2] + (4,), np.uint8)
        out[..., 3] = a[..., 0]
        out[..., 1] = 255 - a[..., 1]
        return self.add(('nrm', path), out, 2)

    def glow(self, path):
        """Colour map for the unlit eyes: a dark eyeball with a smaller, bright yellow iris. (Splatterhouse's own glow map
        is laid out for other UVs: its halo would land beside the iris.)"""
        im = Image.open(path).convert('RGBA')
        size = pow2(*im.size)
        a = np.asarray(im.resize(size, Image.LANCZOS)).astype(np.float32)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        found = (r > 90) & (g > 90) & (b < 0.75 * g)
        # a smaller iris: the ellipse fitted to the found one (its highlight included), scaled about its centre
        ys, xs = np.nonzero(found)
        c = np.array([ys.mean(), xs.mean()])
        cov = np.cov(np.stack([ys, xs])) * 4 * GLOW_SHRINK ** 2       # (a uniform ellipse's radii: 2 sigma)
        yy, xx = np.mgrid[0:found.shape[0], 0:found.shape[1]]
        d = np.stack([yy - c[0], xx - c[1]], -1)
        iris = (np.einsum('...i,ij,...j->...', d, np.linalg.inv(cov), d) <= 1).astype(np.float32)
        iris = np.asarray(Image.fromarray((iris * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(
            max(1, size[0] // 128))), np.float32)[..., None] / 255.0
        a[..., :3] = a[..., :3] * GLOW_DARK * (1 - iris) + GLOW_YELLOW * iris
        a[..., 3] = 255
        return self.add(('glow', path), np.clip(a, 0, 255).astype(np.uint8), 0)

    def constant(self, rgba, fmt, size=32):
        img = np.zeros((size, size, 4), np.uint8)
        img[:] = rgba
        return self.add(('const', tuple(int(x) for x in rgba), fmt), img, fmt)

    def textures(self, budget=TEXTURE_BUDGET, bloody=False):
        """NUT texture dicts, the largest halved (normal maps first) until they fit the budget. bloody: with the
        clothes' original blood (the same sizes and order, so either NUT goes with the NUD)."""
        imgs = [self.bloody.get(i, im) if bloody else im for i, im in enumerate(self.images)]

        def size(i):
            h, w = imgs[i].shape[:2]
            return sum(max(1, (w >> k) // 4) * max(1, (h >> k) // 4) * (8 if self.fmts[i] == 0 else 16)
                       for k in range(MIPS))
        while sum(size(i) for i in range(len(imgs))) > budget:
            big = [i for i in range(len(imgs)) if min(imgs[i].shape[:2]) > 64]
            if not big:
                break
            i = max(big, key=lambda i: size(i) * (2 if self.fmts[i] == 2 and imgs[i][..., 0].max() == 0 else 1))
            h, w = imgs[i].shape[:2]
            imgs[i] = (imgs[i].reshape(h // 2, 2, w // 2, 2, 4).astype(np.float32).mean((1, 3)) + 0.5
                       ).astype(np.uint8)
        return [nut.make_texture(im, GIDX_FIRST + i, f, mips=MIPS) for i, (im, f) in enumerate(zip(imgs, self.fmts))]


def seam_scale(bank, info, data, tex_dir):
    """Each SKIN_MESHES texture's factor on its graded skin: the body's graded colour over its own at the vertices
    it shares with the body (SKIN_TEXTURE) meshes, medians per channel, sampled through a small blur."""
    scratch = TextureBank(skin_target=bank.skin_target)

    def graded(name):
        path = os.path.join(tex_dir, name.replace('.dds', '.png'))
        img = Image.fromarray(scratch.images[scratch.colour(path, False, skin=True) - GIDX_FIRST])
        return path, np.asarray(img.filter(ImageFilter.BoxBlur(2)), np.float64)[..., :3]

    def sample(img, uv):
        h, w = img.shape[:2]
        return img[np.clip((uv[:, 1] % 1) * h, 0, h - 1).astype(int), np.clip((uv[:, 0] % 1) * w, 0, w - 1).astype(int)]
    meshes = list(enumerate(info['meshes']))
    body = [k for k, m in meshes if m['textures']['base'] == SKIN_TEXTURE]
    _, body_img = graded(SKIN_TEXTURE)
    for k, m in meshes:
        if m['name'] not in SKIN_MESHES:
            continue
        pos, uv = data['mesh%d_positions' % k], data['mesh%d_uv' % k]
        mine, theirs = [], []
        for b in body:
            near = np.linalg.norm(pos[:, None] - data['mesh%d_positions' % b][None], axis=2) < 0.5
            i, j = np.nonzero(near)
            mine.append(i)
            theirs.append(sample(body_img, data['mesh%d_uv' % b][j]))
        i = np.concatenate(mine)
        if not len(i):
            continue
        path, img = graded(m['textures']['base'])
        ratio = np.median(np.concatenate(theirs) / np.maximum(sample(img, uv[i]), 1.0), 0)
        bank.skin_scale[path] = bank.skin_scale.get(path, 1.0) * ratio
        print('%s: skin graded x %s to the body at %d seam vertices' % (m['name'], np.round(ratio, 3), len(i)))


def templates(arc):
    """{kind: (material, [slot mean RGBA], [slot format])} from TEMPLATES."""
    def read(ref):
        return arc.read_name(ref) if isinstance(ref, str) else arc.read(ref)
    tex = {}
    for src in TEMPLATE_TEXTURES:
        tex.update({t['gidx']: t for t in xbox.read_nut(read(src))['textures']})
    out = {}
    for kind, (src, mesh, poly) in TEMPLATES.items():
        find = {m['name']: m for m in xbox.read_nud(read(src))['meshes']}
        mat = find[mesh]['polys'][poly]['materials'][0]
        means = [xbox.decode_texture(tex[t['id']]).reshape(-1, 4).mean(0).round().astype(int) if t['id'] in tex
                 else np.array([128, 128, 128, 255]) for t in mat['textures']]
        fmts = [tex[t['id']]['fmt'] if t['id'] in tex else 0 for t in mat['textures']]
        out[kind] = (mat, means, fmts)
    return out


def tangents(pos, nrm, uv, tris):
    """TTT2's tangent frame per vertex: tangent +dP/du, bitangent -dP/dv (Petexy)."""
    a, b, c = tris.T
    e1, e2 = pos[b] - pos[a], pos[c] - pos[a]
    du1, dv1 = uv[b, 0] - uv[a, 0], uv[b, 1] - uv[a, 1]
    du2, dv2 = uv[c, 0] - uv[a, 0], uv[c, 1] - uv[a, 1]
    det = du1 * dv2 - du2 * dv1
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, det, 1)[:, None]
    dPdu = (e1 * dv2[:, None] - e2 * dv1[:, None]) / inv
    dPdv = (e2 * du1[:, None] - e1 * du2[:, None]) / inv
    tu, tv = np.zeros_like(pos), np.zeros_like(pos)
    for col in (a, b, c):
        np.add.at(tu, col[ok], dPdu[ok])
        np.add.at(tv, col[ok], dPdv[ok])
    tan = tu - nrm * (tu * nrm).sum(1, keepdims=True)
    bad = np.linalg.norm(tan, axis=1) < 1e-9
    tan[bad] = np.cross(nrm[bad], [0, 1, 0]) + 1e-6
    tan /= np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-12)
    bit = np.cross(nrm, tan)
    bit *= np.where((bit * -tv).sum(1) >= 0, 1.0, -1.0)[:, None]
    return tan, bit


def shiny(tex_dir, textures, out):
    """A colour map for the chain: the gloss map's brightness in the base map's hue (written to out, its path)."""
    base = np.asarray(Image.open(os.path.join(tex_dir, textures['base'].replace('.dds', '.png'))).convert('RGBA'))
    gloss = Image.open(os.path.join(tex_dir, textures['gloss'].replace('.dds', '.png'))).convert('L')
    gloss = np.asarray(gloss.resize(base.shape[1::-1], Image.LANCZOS), np.float32)[..., None]
    hue = base[..., :3] / np.maximum(base[..., :3].mean(-1, keepdims=True), 1.0)
    img = base.copy()
    img[..., :3] = np.clip(gloss * CHAIN_SHINE * hue + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(img).save(out)
    return out


def in_front(pos, cover, cover_tris, gap):
    """pos with each vertex behind the cover mesh's front surface (+z, the side he faces) at its x, y moved to gap in
    front of it."""
    a, b, c = (cover[cover_tris[:, i]] for i in range(3))
    v0, v1 = b[:, :2] - a[:, :2], c[:, :2] - a[:, :2]
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    ok = np.abs(den) > 1e-9
    den = np.where(ok, den, 1.0)
    out = pos.copy()
    for i, p in enumerate(pos):
        v2 = p[:2] - a[:, :2]
        u = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
        v = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1)
        if hit.any():
            front = (a[:, 2] + u * (b[:, 2] - a[:, 2]) + v * (c[:, 2] - a[:, 2]))[hit].max()
            out[i, 2] = max(p[2], front + gap)
    return out


def polygon(pos, nrm, uv, tris, bones, wts, mat):
    if float(((np.cross(pos[tris[:, 1]] - pos[tris[:, 0]], pos[tris[:, 2]] - pos[tris[:, 0]])
               * nrm[tris].sum(1)).sum(1) < 0).mean()) > 0.5:
        tris = tris[:, [0, 2, 1]]                # TTT2 front faces are counter-clockwise around the normal
    tan, bit = tangents(pos, nrm, uv, tris)
    verts = np.zeros(len(pos), nud.vertex_dtype(0x13, 0x10))
    verts['pos'] = pos
    verts['pw'] = 100.0
    verts['nrm'][:, :3], verts['nrm'][:, 3] = nrm, 1.0
    verts['tan'][:, :3], verts['tan'][:, 3] = tan, 1.0
    verts['bitan'][:, :3], verts['bitan'][:, 3] = bit, 1.0
    verts['bones'], verts['w'] = bones, wts
    verts['uv'][:, 0, :] = uv
    strip = strips.stripify(tris)
    if not strips.check(tris, strip) or len(strip) >= 0x10000 or len(pos) >= 0xFFFF:
        raise ValueError('could not make triangle strips')
    return dict(vtype=0x13, uvtype=0x10, pflag=4, tail=bytes(12), indices=np.array(strip, np.uint16), verts=verts,
                materials=[mat])


def convert(game, rick_dir, tex_dir, out):
    arc = Archives(game)
    donor = xbox.read_bone(arc.read_name(DONOR + '.bon'))
    dnames = [n[4:] if n.startswith('cha:') else n for n in donor['names']]
    dW = bone.world_matrices(donor)
    dpos = {n: dW[i][:3, 3] for i, n in enumerate(dnames)}
    info = json.load(open(os.path.join(rick_dir, 'model.json')))
    data = np.load(os.path.join(rick_dir, 'model.npz'))
    names, parents = info['skeleton']['names'], info['skeleton']['parents']
    P = data['skeleton_world'][:, :3, 3].astype(np.float64)

    D = reposed(names, parents, P, dpos, info, data)
    P2 =np.array([_apply(D[j], P[j]) for j in range(len(names))])
    t7 = {'names': list(ANCHOR), 'parents': [-1] * len(ANCHOR),
          'world': np.array([np.vstack([np.hstack([np.eye(3), P2[names.index(r)][:, None]]), [0, 0, 0, 1]])
                             for r in ANCHOR.values()])}
    skel = skeleton.build(t7, donor)
    foot_heights(skel, names, P)
    bidx = {n: i for i, n in enumerate(dnames)}
    jmap = np.array([bidx[WEIGHTS.get(n, 'KOSHI_jnt')] for n in names])

    tmpl = templates(arc)
    mtex = {t['gidx']: t for t in xbox.read_nut(arc.read_name(DONOR + '.nut'))['textures']}
    theirs = skin_median(np.concatenate([xbox.decode_texture(mtex[g]).reshape(-1, 4) for g in MARDUK_SKIN]))
    mine = skin_median(np.asarray(Image.open(os.path.join(tex_dir, SKIN_TEXTURE.replace('.dds', '.png'))).convert('RGBA')))
    bank = TextureBank(skin_target=mine * (theirs / mine * RENDER_TRIM))
    print('skin grade (Marduk / Rick x render trim, RGB):', np.round(theirs / mine * RENDER_TRIM, 3))
    seam_scale(bank, info, data, tex_dir)
    meshes, preview, images = [], [], {}
    posed = [skin(D, data['mesh%d_positions' % k].astype(np.float64), data['mesh%d_normals' % k].astype(np.float64),
                  data['mesh%d_joints' % k], data['mesh%d_weights' % k].astype(np.float64))
             for k in range(len(info['meshes']))]
    mesh_names = [m['name'] for m in info['meshes']]
    for k, m in enumerate(info['meshes']):
        pos, nrm = posed[k]
        if m['name'] == CHAIN and CHAIN_COVER in mesh_names:
            cover = mesh_names.index(CHAIN_COVER)
            pos = in_front(pos, posed[cover][0], data['mesh%d_triangles' % cover], CHAIN_GAP)
        uv = data['mesh%d_uv' % k].astype(np.float64)
        tris = data['mesh%d_triangles' % k]
        tj, tw = jmap[data['mesh%d_joints' % k]], data['mesh%d_weights' % k]
        bones, wts = np.zeros((len(pos), 4), np.uint32), np.zeros((len(pos), 4), np.float32)
        for v in range(len(pos)):
            acc = {}
            for j, w in zip(tj[v], tw[v]):
                if w > 0:
                    acc[int(j)] = acc.get(int(j), 0.0) + float(w)
            top = sorted(acc.items(), key=lambda x: -x[1])[:4]
            s = sum(w for _, w in top)
            for q in range(4):
                bones[v, q], wts[v, q] = (top[q][0], top[q][1] / s) if q < len(top) else (top[0][0], 0.0)
        kind = 'overlay' if m['name'] in OVERLAY_MESHES else 'glow' if m['name'] in GLOW_MESHES \
            else 'skin' if m['textures']['base'] == SKIN_TEXTURE or m['name'] in SKIN_MESHES \
            else 'cloth'
        mat, means, fmts = tmpl[kind]
        mat = json.loads(json.dumps(mat, default=lambda b: b.hex()))     # deep copy (bytes -> hex, restored below)
        for t, src in zip(mat['textures'], tmpl[kind][0]['textures']):
            t['pad4'], t['tail'] = src['pad4'], src['tail']
        base = os.path.join(tex_dir, m['textures']['base'].replace('.dds', '.png'))
        if m['name'] == CHAIN and 'gloss' in m['textures']:
            os.makedirs(out, exist_ok=True)
            base = shiny(tex_dir, m['textures'], os.path.join(out, 'chain_base.png'))
        normal = m['textures'].get('normal')
        for i, t in enumerate(mat['textures']):
            if i == 0 and kind == 'glow':
                t['id'] = bank.glow(base)
            elif i == 0:
                t['id'] = bank.colour(base, kind == 'overlay', skin=kind == 'skin' or m['name'] in SKIN_SHARING)
            elif normal and abs(int(means[i][1]) - 128) < 16 and abs(int(means[i][3]) - 128) < 16:   # a normal map slot
                t['id'] = bank.normal(os.path.join(tex_dir, normal.replace('.dds', '.png')))
            else:
                t['id'] = bank.constant(means[i], fmts[i])
            t['wrap_s'] = t['wrap_t'] = 1        # repeat (Splatterhouse UVs run past 0..1)
        poly = polygon(pos, nrm, uv, tris, bones, wts, mat)
        single = bidx['ATAMA_jnt_assist' if m['name'] in HEAD_MESHES else 'KOSHI_jnt']
        sph = nud.bounding_sphere(pos)
        meshes.append(dict(name='rick_' + m['name'], sphere=sph, center=sph[:3], sort_bias=0.0, zero=0,
                           boneflag=0x2c, singlebind=single, polys=[poly]))
        preview.append(dict(name=m['name'], positions=pos, normals=nrm, uv=uv, triangles=tris,
                            textures={'base': base}))
        images[base] = np.asarray(Image.open(base).convert('RGBA'))
    allp = np.concatenate([p['verts']['pos'] for mm in meshes for p in mm['polys']])
    model = dict(version=0x0201, sphere=nud.bounding_sphere(allp), bone_first=None, meshes=meshes)
    textures = bank.textures()

    os.makedirs(os.path.join(out, 'files'), exist_ok=True)
    files = {DONOR + '.nud': xbox.write_nud(model),
             DONOR + '.nut': xbox.write_nut({'version': 0x0100, 'textures': textures, 'trailer': b''}),
             DONOR + '_blood.nut': xbox.write_nut({'version': 0x0100, 'textures': bank.textures(bloody=True),
                                                   'trailer': b''}),
             DONOR + '.bon': xbox.write_bone(skel),
             DONOR + '.xml': itemdb.body_only(arc.read_name(DONOR + '.xml'))}
    for name, b in files.items():
        open(os.path.join(out, 'files', name), 'wb').write(b)
    shots = [render(preview, images, v) for v in VIEWS]
    sheet = Image.new('RGB', (sum(s.width for s in shots), shots[0].height))
    for i, s in enumerate(shots):
        sheet.paste(s, (i * s.width, 0))
    sheet.save(os.path.join(out, 'preview.png'))
    tex_bytes = sum(len(mm) for t in textures for mm in t['mips'])
    print('%s: %d meshes, %d vertices, %d textures (%d KB), height %.0f mm, skeleton scale %.3f' % (
        out, len(meshes), len(allp), len(textures), tex_bytes // 1024, allp[:, 1].max(), skel['scale']))
    for name, b in files.items():
        print('  %-8s %9d bytes' % (name, len(b)))
    return skel, model


if __name__ == '__main__':
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    convert(*sys.argv[1:])
