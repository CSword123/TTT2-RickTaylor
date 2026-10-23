"""A TTT2 fighter's body model, skeleton and textures out of the game, in TTT2 space (mm, Y up, facing +Z, left +X).

python -m ttt2rick.ttt2.extract <game folder> <code> <out dir>      e.g. code `mar` (Marduk)

Reads <code>.nud, <code>.nut and <code>.bon. Writes model.npz (per mesh: positions, normals, uv, triangles, joints,
weights; skeleton_world), model.json (skeleton names/parents, meshes, bounds), <code>.obj/.mtl, textures/<gidx>.png,
and preview.png (front, side, back).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

from . import xbox
from .archive import Archives
from .petexy import bone, nud
from ..splatterhouse.preview import render

# TTT2 space -> camera (x right, y up, z towards the viewer): front, side (from his left, +X), back
VIEWS = [np.eye(3),
         np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], float),
         np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]], float)]


def meshes_of(model):
    """One dict per NUD polygon: name, positions, normals, uv, triangles, joints, weights, textures {'base': gidx}."""
    out = []
    for m in model['meshes']:
        for k, p in enumerate(m['polys']):
            v = p['verts']
            n = len(v)
            joints = v['bones'].astype(np.int16) if 'bones' in v.dtype.names else np.zeros((n, 4), np.int16)
            if 'w' in v.dtype.names:
                w = v['w'].astype(np.float32)
                if v.dtype['w'].base == np.uint8:
                    w = w / 255.0
            else:
                w = np.zeros((n, 4), np.float32)
                w[:, 0] = 1
            if m['singlebind'] >= 0 and 'bones' not in v.dtype.names:
                joints[:, 0] = m['singlebind']
            tex = p['materials'][0]['textures'] if p['materials'] else []
            out.append(dict(name='%s.%d' % (m['name'], k), mesh=m['name'],
                            positions=np.asarray(v['pos'], np.float64),
                            normals=np.asarray(v['nrm'][:, :3], np.float64) if 'nrm' in v.dtype.names
                            else np.zeros((n, 3)),
                            uv=np.asarray(v['uv'][:, 0], np.float64) if 'uv' in v.dtype.names else None,
                            triangles=np.array(nud.strip_to_tris(p['indices']), np.int32).reshape(-1, 3),
                            joints=joints, weights=w,
                            textures={'base': '%08x' % tex[0]['id']} if tex else {}))
    return out


def write_obj(meshes, out, code):
    with open(os.path.join(out, code + '.mtl'), 'w') as f:
        for m in meshes:
            f.write('newmtl %s\n' % m['name'])
            if m['textures'].get('base'):
                f.write('map_Kd textures/%s.png\n' % m['textures']['base'])
            f.write('\n')
    with open(os.path.join(out, code + '.obj'), 'w') as f:
        f.write('mtllib %s.mtl\n' % code)
        base = 1
        for m in meshes:
            uv = m['uv'] if m['uv'] is not None else np.zeros((len(m['positions']), 2))
            f.write('g %s\nusemtl %s\n' % (m['name'], m['name']))
            f.writelines('v %.4f %.4f %.4f\n' % tuple(v) for v in m['positions'])
            f.writelines('vt %.6f %.6f\n' % (u, 1 - v) for u, v in uv)
            f.writelines('vn %.5f %.5f %.5f\n' % tuple(v) for v in m['normals'])
            f.writelines('f %d/%d/%d %d/%d/%d %d/%d/%d\n' % tuple(x for i in t + base for x in (i, i, i))
                         for t in m['triangles'])
            base += len(m['positions'])


def main(game, code, out):
    arc = Archives(game)
    model = xbox.read_nud(arc.read_name(code + '.nud'))
    textures = xbox.read_nut(arc.read_name(code + '.nut'))
    skel = xbox.read_bone(arc.read_name(code + '.bon'))
    os.makedirs(os.path.join(out, 'textures'), exist_ok=True)

    images = {}
    for t in textures['textures']:
        name = '%08x' % t['gidx']
        images[name] = xbox.decode_texture(t)
        Image.fromarray(images[name]).save(os.path.join(out, 'textures', name + '.png'))

    meshes = meshes_of(model)
    world = bone.world_matrices(skel)
    arrays = {'skeleton_world': np.asarray(world, np.float32)}
    allp = np.concatenate([m['positions'] for m in meshes])
    info = {'code': code, 'space': 'TTT2: mm, Y up, facing +Z, left +X',
            'bounds': [allp.min(0).round(1).tolist(), allp.max(0).round(1).tolist()],
            'skeleton': {'names': skel['names'], 'parents': skel['parent'], 'scale': skel['scale']}, 'meshes': []}
    for k, m in enumerate(meshes):
        for f in ('positions', 'normals', 'triangles', 'joints', 'weights'):
            arrays['mesh%d_%s' % (k, f)] = m[f]
        arrays['mesh%d_uv' % k] = m['uv'] if m['uv'] is not None else np.zeros((len(m['positions']), 2))
        info['meshes'].append({'name': m['name'], 'textures': m['textures'], 'vertices': len(m['positions']),
                               'triangles': len(m['triangles']), 'joints': sorted(set(m['joints'].ravel().tolist()))})
    np.savez_compressed(os.path.join(out, 'model.npz'), **arrays)
    with open(os.path.join(out, 'model.json'), 'w') as f:
        json.dump(info, f, indent=1)
    write_obj(meshes, out, code)

    shots = [render(meshes, images, v) for v in VIEWS]
    sheet = Image.new('RGB', (sum(s.width for s in shots), shots[0].height))
    for i, s in enumerate(shots):
        sheet.paste(s, (i * s.width, 0))
    sheet.save(os.path.join(out, 'preview.png'))
    print('%s: %d meshes, %d polygons, %d triangles, %d textures, %d bones; bounds %s' % (
        code, len(model['meshes']), len(meshes), sum(len(m['triangles']) for m in meshes), len(images),
        len(skel['names']), info['bounds']))


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
