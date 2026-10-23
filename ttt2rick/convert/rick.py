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
Writes files/<code>.nud/.nut/.bon/.xml (install that folder with ttt2rick.ttt2.overlay) and preview.png.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

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


class TextureBank:
    def __init__(self):
        self.images, self.fmts, self.keys = [], [], {}

    def add(self, key, rgba, fmt):
        if key not in self.keys:
            self.keys[key] = GIDX_FIRST + len(self.images)
            self.images.append(np.asarray(rgba, np.uint8))
            self.fmts.append(fmt)
        return self.keys[key]

    def colour(self, path, alpha):
        im = Image.open(path).convert('RGBA')
        a = np.array(im.resize(pow2(*im.size), Image.LANCZOS))
        if not alpha:
            a[..., 3] = 255
        return self.add(('img', path, alpha), a, 2 if alpha else 0)

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

    def textures(self, budget=TEXTURE_BUDGET):
        """NUT texture dicts, the largest halved (normal maps first) until they fit the budget."""
        imgs = list(self.images)

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

    D = repose(names, parents, P, dpos)
    # straightened legs reach lower than the bent ones did: stand the soles on the floor (y = 0) again
    floor = min(skin(D, data['mesh%d_positions' % k].astype(np.float64), data['mesh%d_normals' % k].astype(
        np.float64), data['mesh%d_joints' % k], data['mesh%d_weights' % k].astype(np.float64))[0][:, 1].min()
        for k in range(len(info['meshes'])))
    lift = np.eye(4)
    lift[1, 3] = -floor
    D = lift @ D
    P2 =np.array([_apply(D[j], P[j]) for j in range(len(names))])
    t7 = {'names': list(ANCHOR), 'parents': [-1] * len(ANCHOR),
          'world': np.array([np.vstack([np.hstack([np.eye(3), P2[names.index(r)][:, None]]), [0, 0, 0, 1]])
                             for r in ANCHOR.values()])}
    skel = skeleton.build(t7, donor)
    bidx = {n: i for i, n in enumerate(dnames)}
    jmap = np.array([bidx[WEIGHTS.get(n, 'KOSHI_jnt')] for n in names])

    tmpl = templates(arc)
    bank = TextureBank()
    meshes, preview, images = [], [], {}
    for k, m in enumerate(info['meshes']):
        pos, nrm = skin(D, data['mesh%d_positions' % k].astype(np.float64), data['mesh%d_normals' % k].astype(
            np.float64), data['mesh%d_joints' % k], data['mesh%d_weights' % k].astype(np.float64))
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
            else 'skin' if m['textures']['base'] == SKIN_TEXTURE else 'cloth'
        mat, means, fmts = tmpl[kind]
        mat = json.loads(json.dumps(mat, default=lambda b: b.hex()))     # deep copy (bytes -> hex, restored below)
        for t, src in zip(mat['textures'], tmpl[kind][0]['textures']):
            t['pad4'], t['tail'] = src['pad4'], src['tail']
        base = os.path.join(tex_dir, m['textures']['base'].replace('.dds', '.png'))
        normal = m['textures'].get('normal')
        for i, t in enumerate(mat['textures']):
            if i == 0 and kind == 'glow':
                t['id'] = bank.glow(base)
            elif i == 0:
                t['id'] = bank.colour(base, kind == 'overlay')
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
