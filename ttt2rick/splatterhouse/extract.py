"""Rick out of Splatterhouse: each costume state's skeleton, skinned meshes and textures, in TTT2's space, for the
TTT2 converter (and an OBJ to look at).

python3 -m ttt2rick.splatterhouse.extract <Splatterhouse data folder or rick.nif> <out folder>

Out, per state (brawler, berserker):
  <state>/model.npz      per mesh k: mesh{k}_positions (v, 3) mm, _normals, _uv, _triangles, _joints (v, 4) skeleton
                         indices, _weights (v, 4); skeleton_world (j, 4, 4) bind matrices
  <state>/model.json     skeleton names / parents, meshes (name, material, textures)
  <state>/rick.obj, .mtl the bind pose, for a modelling program
  textures/*.png         every texture of the file (top mip)

TTT2 space: millimetres, Y up, the fighter facing +Z with his left at +X. Gamebryo's (Z up, facing +X, left +Y)
goes there by the cyclic swap (x, y, z) -> (y, z, x): a rotation, so nothing is mirrored.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

from . import rickmodel
from ..common import x360tex

RICK_NIF = 'characters/rick_havok/xbox360/rick.nif'
M_TO_MM = 1000.0
# Gamebryo -> TTT2 axes: new = SWAP @ old
SWAP = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)


def to_ttt2_points(p):
    return (p @ SWAP.T) * M_TO_MM


def to_ttt2_dirs(d):
    return d @ SWAP.T


def to_ttt2_matrix(m):
    out = np.repeat(np.eye(4)[None], len(m), 0)
    out[:, :3, :3] = SWAP @ m[:, :3, :3] @ SWAP.T
    out[:, :3, 3] = to_ttt2_points(m[:, :3, 3])
    return out


def find_nif(src):
    if os.path.isdir(src):
        for cand in (os.path.join(src, RICK_NIF), os.path.join(src, 'data', RICK_NIF)):
            if os.path.exists(cand):
                return cand
        raise SystemExit('no %s under %s' % (RICK_NIF, src))
    return src


def export_state(model, state, out):
    os.makedirs(out, exist_ok=True)
    skel = model.skeleton()
    meshes = [model.mesh(i, skel) for i in model.visible_meshes(state)]
    arrays = {'skeleton_world': to_ttt2_matrix(skel['world'])}
    info = {'state': state, 'space': 'TTT2: mm, Y up, facing +Z, left +X',
            'skeleton': {'names': skel['names'], 'parents': skel['parents']}, 'meshes': []}
    for k, m in enumerate(meshes):
        arrays['mesh%d_positions' % k] = to_ttt2_points(m['positions']).astype(np.float32)
        arrays['mesh%d_normals' % k] = to_ttt2_dirs(m['normals']).astype(np.float32)
        arrays['mesh%d_uv' % k] = (m['uv'] if m['uv'] is not None else np.zeros((len(m['positions']), 2))
                                   ).astype(np.float32)
        arrays['mesh%d_triangles' % k] = m['triangles'].astype(np.int32)
        arrays['mesh%d_joints' % k] = m['joints'].astype(np.int16)
        arrays['mesh%d_weights' % k] = m['weights'].astype(np.float32)
        info['meshes'].append({'name': m['name'], 'material': m['material'], 'textures': m['textures'],
                               'vertices': len(m['positions']), 'triangles': len(m['triangles'])})
    np.savez_compressed(os.path.join(out, 'model.npz'), **arrays)
    with open(os.path.join(out, 'model.json'), 'w') as f:
        json.dump(info, f, indent=1)
    write_obj(meshes, out)
    return meshes


def write_obj(meshes, out):
    """The bind pose in TTT2 space (mm), one group per mesh, materials pointing at ../textures."""
    with open(os.path.join(out, 'rick.mtl'), 'w') as f:
        for m in meshes:
            f.write('newmtl %s\n' % m['name'])
            base = m['textures'].get('base')
            if base:
                f.write('map_Kd ../textures/%s\n' % base.replace('.dds', '.png'))
            f.write('\n')
    with open(os.path.join(out, 'rick.obj'), 'w') as f:
        f.write('mtllib rick.mtl\n')
        base = 1
        for m in meshes:
            p = to_ttt2_points(m['positions'])
            n = to_ttt2_dirs(m['normals'])
            uv = m['uv'] if m['uv'] is not None else np.zeros((len(p), 2))
            f.write('g %s\nusemtl %s\n' % (m['name'], m['name']))
            f.writelines('v %.4f %.4f %.4f\n' % tuple(v) for v in p)
            f.writelines('vt %.6f %.6f\n' % (u, 1 - v) for u, v in uv)
            f.writelines('vn %.5f %.5f %.5f\n' % tuple(v) for v in n)
            f.writelines('f %d/%d/%d %d/%d/%d %d/%d/%d\n' % tuple(x for i in t + base for x in (i, i, i))
                         for t in m['triangles'])
            base += len(p)


def main(src, out):
    model = rickmodel.load(find_nif(src))
    tex_dir = os.path.join(out, 'textures')
    os.makedirs(tex_dir, exist_ok=True)
    for name, block in sorted(model.texture_blocks().items()):
        Image.fromarray(x360tex.decode(block)).save(os.path.join(tex_dir, name.replace('.dds', '.png')))
    for state in rickmodel.STATES:
        meshes = export_state(model, state, os.path.join(out, state))
        print('%-10s %2d meshes %6d vertices %6d triangles' % (
            state, len(meshes), sum(len(m['positions']) for m in meshes), sum(len(m['triangles']) for m in meshes)))
    print('textures  %d -> %s' % (len(os.listdir(tex_dir)), tex_dir))


if __name__ == '__main__':
    main(*sys.argv[1:])
