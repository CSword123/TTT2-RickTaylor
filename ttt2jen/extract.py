"""Jennifer out of Splatterhouse: her skeleton, skinned meshes and textures, in TTT2's space, in the form
ttt2rick.splatterhouse.extract gives Rick's (model.npz / model.json / textures/*.png).

python -m ttt2jen.extract <Splatterhouse data folder or jennifer.nif> <out folder, e.g. work/jennifer>

Her file has one outfit (T-shirt, jeans, belt, sneakers; no costume switches): every mesh is taken.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

from ttt2rick.common import x360tex
from ttt2rick.splatterhouse import rickmodel
from ttt2rick.splatterhouse.extract import to_ttt2_dirs, to_ttt2_matrix, to_ttt2_points

JEN_NIF = 'characters/jennifer/xbox360/jennifer.nif'


def find_nif(src):
    if os.path.isdir(src):
        for cand in (os.path.join(src, JEN_NIF), os.path.join(src, 'data', JEN_NIF)):
            if os.path.exists(cand):
                return cand
        raise SystemExit('no %s under %s' % (JEN_NIF, src))
    return src


def main(src, out):
    model = rickmodel.load(find_nif(src))
    tex_dir = os.path.join(out, 'textures')
    os.makedirs(tex_dir, exist_ok=True)
    for name, block in sorted(model.texture_blocks().items()):
        Image.fromarray(x360tex.decode(block)).save(os.path.join(tex_dir, name.replace('.dds', '.png')))
    skel = model.skeleton()
    meshes = [model.mesh(i, skel) for i, b in sorted(model.blocks.items()) if b['type'] == 'NiMesh']
    arrays = {'skeleton_world': to_ttt2_matrix(skel['world'])}
    info = {'state': 'jennifer', 'space': 'TTT2: mm, Y up, facing +Z, left +X',
            'skeleton': {'names': skel['names'], 'parents': skel['parents']}, 'meshes': []}
    for k, m in enumerate(meshes):
        arrays['mesh%d_positions' % k] = to_ttt2_points(m['positions']).astype(np.float32)
        arrays['mesh%d_normals' % k] = to_ttt2_dirs(m['normals']).astype(np.float32)
        arrays['mesh%d_uv' % k] = m['uv'].astype(np.float32)
        arrays['mesh%d_triangles' % k] = m['triangles'].astype(np.int32)
        arrays['mesh%d_joints' % k] = m['joints'].astype(np.int16)
        arrays['mesh%d_weights' % k] = m['weights'].astype(np.float32)
        info['meshes'].append({'name': m['name'], 'material': m['material'], 'textures': m['textures'],
                               'vertices': len(m['positions']), 'triangles': len(m['triangles'])})
    np.savez_compressed(os.path.join(out, 'model.npz'), **arrays)
    with open(os.path.join(out, 'model.json'), 'w') as f:
        json.dump(info, f, indent=1)
    print('%d meshes, %d vertices, %d joints, %d textures -> %s' % (
        len(meshes), sum(len(m['positions']) for m in meshes), len(skel['names']), len(os.listdir(tex_dir)), out))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
