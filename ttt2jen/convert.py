"""Jennifer -> a TTT2 fighter's body files under her own code (`jen`), on Nina's skeleton, as ttt2rick.convert.rick
makes Rick's (its helpers: repose, skeleton, materials, textures).

python -m ttt2jen.convert <game folder> <her export (ttt2jen.extract's out, e.g. work/jennifer)> <out dir>

- Skeleton: Nina's (`nin`, DONOR): about her size (head 1555 mm; Jennifer's 1516 mm) and with the chest's spring bone
  OPT0_munetop, which the game moves as the other women's busts: her breast joints' weights go to it. Its joints moved
  to hers by Petexy's skeleton.build; the scale is her hips' height / 1150 (0.83).
- Repose: her bind pose is an A-pose; each limb turned to Nina's T-pose directions (AIM, ROLL), the soles back on the
  floor.
- Materials: skin for her face and the bare skin of her body mesh (whose one texture holds her skin, T-shirt and
  jeans: its triangles are split by the texture under them, skin_weight at their UV centre), blended overlay for the
  hair cards, scalp and lashes (alpha), cloth for the rest. Her skin is graded as Rick's (RENDER_TRIM: TTT2's
  lighting darkens Splatterhouse's painted shading), to her own face's colour.
- UVs: Splatterhouse tiles some of hers (her body mesh's V runs 0-2, the shoes' U too) and TTT2 does not repeat
  textures, so each vertex is moved back into 0-1 by its triangles' tile (no vertex is shared between tiles).
- Clothing: she is dressed in every Splatterhouse texture (T-shirt and jeans; nothing under them), so nothing is
  hidden or censored.
Writes files/jen.nud/.nut/.bon/.xml and preview.png.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

from ttt2rick.convert import rick as rc
from ttt2rick.splatterhouse.preview import render
from ttt2rick.ttt2 import xbox
from ttt2rick.ttt2.archive import Archives
from ttt2rick.ttt2.extract import VIEWS
from ttt2rick.ttt2.petexy import bone, itemdb, nud, skeleton

DONOR, CODE = 'nin', 'jen'
FACE_TEXTURE = 'jeni_face_color.dds'
BODY_TEXTURE = 'jennifer_body_02_color.dds'          # skin, T-shirt and jeans: split by skin_weight
OVERLAY_TEXTURES = {'hair_combine_color.dds', 'jeni_head_02.dds'}
HEAD_FROM = 1400.0                                   # mm: meshes above this height are bound to the head

# Jennifer joint -> TTT2 bone its skin weights go to (TTT2 names without 'cha:')
WEIGHTS = {'root_jnt': 'KOSHI_jnt', 'm_hips_jnt': 'KOSHI_jnt', 'm_spine1_jnt': 'MUNE1_jnt',
           'm_spine2_jnt': 'MUNE1_jnt', 'm_spine3_jnt': 'MUNE2_jnt', 'm_neck_jnt': 'KUBI_jnt_assist',
           'm_head_jnt': 'ATAMA_jnt_assist', 'l_brest_jnt': 'OPT0_munetop', 'r_brest_jnt': 'OPT0_munetop'}
# Tekken 7 joint name (Petexy's skeleton.ANCHOR) -> the joint of hers whose position it takes
ANCHOR = {'BASE': 'm_hips_jnt', 'Hip': 'm_hips_jnt', 'Spine1': 'm_spine1_jnt', 'Spine2': 'm_spine3_jnt',
          'Neck': 'm_neck_jnt', 'Head': 'm_head_jnt'}
AIM = []
FINGERS = (('thumb', 'Thumb', 'OYA'), ('index', 'Index', 'HITO'), ('mid', 'Middle', 'NAKA'),
           ('ring', 'Ring', 'KUSU'), ('pinky', 'Pinky', 'KO'))
for S, s in (('L', 'l'), ('R', 'r')):
    WEIGHTS.update({'%s_clavical_jnt' % s: 'SAKOTSU_%s_jnt' % S, '%s_shoulder_jnt' % s: 'KATA_0_%s_jnt' % S,
                    '%s_shoulder_twist_jnt' % s: 'KATA_50_%s' % S, '%s_elbow_jnt' % s: 'UDE_%s_jnt' % S,
                    '%s_forearm_01_jnt' % s: 'UDE_50_%s' % S, '%s_forearm_02_jnt' % s: 'UDE_50_%s' % S,
                    '%s_wrist_jnt' % s: 'TE_%s_jnt' % S, '%s_weapon_jnt' % s: 'TE_%s_jnt' % S,
                    '%s_thi_jnt' % s: 'MOMO_0_%s' % S, '%s_shin_jnt' % s: 'SUNE_%s' % S,
                    '%s_foot_jnt' % s: 'ASHI_%s_jnt' % S, '%s_navicular_jnt' % s: 'TSUMASAKI_%s_jnt' % S})
    ANCHOR.update({'%s_Shoulder' % S: '%s_clavical_jnt' % s, '%s_Arm' % S: '%s_shoulder_jnt' % s,
                   '%s_ForeArm' % S: '%s_elbow_jnt' % s, '%s_Hand' % S: '%s_wrist_jnt' % s,
                   '%s_UpLeg' % S: '%s_thi_jnt' % s, '%s_Leg' % S: '%s_shin_jnt' % s,
                   '%s_Foot' % S: '%s_foot_jnt' % s, '%s_Toe' % S: '%s_navicular_jnt' % s})
    AIM += [(('%s_shoulder_jnt' % s, '%s_elbow_jnt' % s), ('KATA_%s_jnt' % S, 'UDE_%s_jnt' % S)),
            (('%s_elbow_jnt' % s, '%s_wrist_jnt' % s), ('UDE_%s_jnt' % S, 'TE_%s_jnt' % S)),
            (('%s_wrist_jnt' % s, '%s_midFinger_01_jnt' % S), ('TE_%s_jnt' % S, 'NAKA3_%s' % S)),
            (('%s_thi_jnt' % s, '%s_shin_jnt' % s), ('MOMO_%s_jnt' % S, 'HIZA_%s_jnt' % S)),
            (('%s_shin_jnt' % s, '%s_foot_jnt' % s), ('HIZA_%s_jnt' % S, 'ASHI_%s_jnt' % S)),
            (('%s_foot_jnt' % s, '%s_navicular_jnt' % s), ('ASHI_%s_jnt' % S, 'TSUMASAKI_%s_jnt' % S))]
    for hers, t7, ttt2 in FINGERS:
        for k in (1, 2, 3):                      # her _01 = proximal = TTT2 3 = Tekken 7 1
            WEIGHTS['%s_%sFinger_%02d_jnt' % (S, hers, k)] = '%s%d_%s' % (ttt2, 4 - k, S)
            ANCHOR['%s_%s%d' % (S, t7, k)] = '%s_%sFinger_%02d_jnt' % (S, hers, k)
        for k in (1, 2):
            AIM.append((('%s_%sFinger_%02d_jnt' % (S, hers, k), '%s_%sFinger_%02d_jnt' % (S, hers, k + 1)),
                        ('%s%d_%s' % (ttt2, 4 - k, S), '%s%d_%s' % (ttt2, 3 - k, S))))
ROLL = {'%s_wrist_jnt' % s: (('%s_indexFinger_01_jnt' % S, '%s_pinkyFinger_01_jnt' % S),
                             ('HITO3_%s' % S, 'KO3_%s' % S)) for S, s in (('L', 'l'), ('R', 'r'))}
FOOT_JOINTS = ('l_foot_jnt', 'r_foot_jnt', 'l_navicular_jnt', 'r_navicular_jnt')


def weight_target(name):
    """The TTT2 bone a joint of hers weighs on: WEIGHTS, else the face, eyes, jaw and hair on the head, the
    dress joints (no dress in this outfit) on the hips."""
    if name in WEIGHTS:
        return WEIGHTS[name]
    if name.startswith('m_dress'):
        return 'KOSHI_jnt'
    return 'ATAMA_jnt_assist'


def untiled(uv, tris):
    """uv with each vertex moved by the whole tile (floor of its triangles' UV centre) it is in, into 0-1."""
    tile = np.floor(uv[tris].mean(1))
    out = uv.copy()
    for col in range(3):
        out[tris[:, col]] = uv[tris[:, col]] - tile
    return out


def split_skin(tris, uv, texture):
    """tris' rows whose texture under their UV centre is skin (rc.skin_weight > 0.5), and the others."""
    img = np.asarray(Image.open(texture).convert('RGBA'))
    h, w = img.shape[:2]
    c = uv[tris].mean(1)
    px = img[np.clip((c[:, 1] % 1) * h, 0, h - 1).astype(int), np.clip((c[:, 0] % 1) * w, 0, w - 1).astype(int)]
    skin = rc.skin_weight(px[None])[0] > 0.5
    return tris[skin], tris[~skin]


def convert(game, jen_dir, out):
    arc = Archives(game)
    tex_dir = os.path.join(jen_dir, 'textures')
    donor = xbox.read_bone(arc.read_name(DONOR + '.bon'))
    dnames = [n[4:] if n.startswith('cha:') else n for n in donor['names']]
    dW = bone.world_matrices(donor)
    dpos = {n: dW[i][:3, 3] for i, n in enumerate(dnames)}
    info = json.load(open(os.path.join(jen_dir, 'model.json')))
    data = np.load(os.path.join(jen_dir, 'model.npz'))
    names, parents = info['skeleton']['names'], info['skeleton']['parents']
    P = data['skeleton_world'][:, :3, 3].astype(np.float64)

    D = rc.reposed(names, parents, P, dpos, info, data, AIM, ROLL)
    P2 = np.array([rc._apply(D[j], P[j]) for j in range(len(names))])
    t7 = {'names': list(ANCHOR), 'parents': [-1] * len(ANCHOR),
          'world': np.array([np.vstack([np.hstack([np.eye(3), P2[names.index(r)][:, None]]), [0, 0, 0, 1]])
                             for r in ANCHOR.values()])}
    skel = skeleton.build(t7, donor)
    rc.foot_heights(skel, names, P, FOOT_JOINTS)
    bidx = {n: i for i, n in enumerate(dnames)}
    jmap = np.array([bidx[weight_target(n)] for n in names])

    tmpl = rc.templates(arc)
    face = rc.skin_median(np.asarray(Image.open(os.path.join(tex_dir, FACE_TEXTURE.replace('.dds', '.png')))
                                     .convert('RGBA')))
    bank = rc.TextureBank(skin_target=face * rc.RENDER_TRIM)

    def material(kind, base, normal):
        mat, means, fmts = tmpl[kind]
        mat = json.loads(json.dumps(mat, default=lambda b: b.hex()))     # deep copy (bytes -> hex, restored below)
        for t, src in zip(mat['textures'], tmpl[kind][0]['textures']):
            t['pad4'], t['tail'] = src['pad4'], src['tail']
        for i, t in enumerate(mat['textures']):
            if i == 0:
                t['id'] = bank.colour(base, kind == 'overlay', skin=kind == 'skin')
            elif normal and abs(int(means[i][1]) - 128) < 16 and abs(int(means[i][3]) - 128) < 16:   # a normal slot
                t['id'] = bank.normal(os.path.join(tex_dir, normal.replace('.dds', '.png')))
            else:
                t['id'] = bank.constant(means[i], fmts[i])
            t['wrap_s'] = t['wrap_t'] = 1
        return mat

    def weights(k):
        tj, tw = jmap[data['mesh%d_joints' % k]], data['mesh%d_weights' % k]
        bones, wts = np.zeros((len(tj), 4), np.uint32), np.zeros((len(tj), 4), np.float32)
        for v in range(len(tj)):
            acc = {}
            for j, w in zip(tj[v], tw[v]):
                if w > 0:
                    acc[int(j)] = acc.get(int(j), 0.0) + float(w)
            top = sorted(acc.items(), key=lambda x: -x[1])[:4]
            s = sum(w for _, w in top)
            for q in range(4):
                bones[v, q], wts[v, q] = (top[q][0], top[q][1] / s) if q < len(top) else (top[0][0], 0.0)
        return bones, wts

    meshes, preview, images = [], [], {}
    for k, m in enumerate(info['meshes']):
        pos, nrm = rc.skin(D, data['mesh%d_positions' % k].astype(np.float64),
                           data['mesh%d_normals' % k].astype(np.float64), data['mesh%d_joints' % k],
                           data['mesh%d_weights' % k].astype(np.float64))
        tris = data['mesh%d_triangles' % k]
        uv = untiled(data['mesh%d_uv' % k].astype(np.float64), tris)
        bones, wts = weights(k)
        tex = m['textures']['base']
        base = os.path.join(tex_dir, tex.replace('.dds', '.png'))
        if tex in OVERLAY_TEXTURES:
            parts = [('overlay', tris)]
        elif tex == FACE_TEXTURE:
            parts = [('skin', tris)]
        elif tex == BODY_TEXTURE and len(tris) > 1000:
            skin_tris, cloth_tris = split_skin(tris, uv, base)
            parts = [('skin', skin_tris), ('cloth', cloth_tris)]
        else:
            parts = [('cloth', tris)]
        head = data['mesh%d_positions' % k][:, 1].min() > HEAD_FROM
        for kind, part in parts:
            if not len(part):
                continue
            used = np.unique(part)
            remap = np.full(len(pos), -1)
            remap[used] = np.arange(len(used))
            sub = (pos[used], nrm[used], uv[used], remap[part])
            poly = rc.polygon(*sub, bones[used], wts[used], material(kind, base, m['textures'].get('normal')))
            sph = nud.bounding_sphere(sub[0])
            name = '%s_%s%s' % (CODE, m['name'].replace(':', '_'), '' if len(parts) == 1 else '_' + kind)
            meshes.append(dict(name=name, sphere=sph, center=sph[:3], sort_bias=0.0, zero=0, boneflag=0x2c,
                               singlebind=bidx['ATAMA_jnt_assist' if head else 'KOSHI_jnt'], polys=[poly]))
            preview.append(dict(name=name, positions=sub[0], normals=sub[1], uv=sub[2], triangles=sub[3],
                                textures={'base': base}))
            images[base] = np.asarray(Image.open(base).convert('RGBA'))
    allp = np.concatenate([p['verts']['pos'] for mm in meshes for p in mm['polys']])
    model = dict(version=0x0201, sphere=nud.bounding_sphere(allp), bone_first=None, meshes=meshes)
    textures = bank.textures()
    os.makedirs(os.path.join(out, 'files'), exist_ok=True)
    files = {CODE + '.nud': xbox.write_nud(model),
             CODE + '.nut': xbox.write_nut({'version': 0x0100, 'textures': textures, 'trailer': b''}),
             CODE + '.bon': xbox.write_bone(skel),
             CODE + '.xml': itemdb.body_only(arc.read_name(DONOR + '.xml'))}
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


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    convert(*sys.argv[1:])
