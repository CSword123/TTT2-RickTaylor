"""Software renders of a converted model (numpy z-buffer, textured, Lambert), to check a conversion by eye.

python3 -m ttt2rick.splatterhouse.preview <rick.nif, compressed or not> <out.png> [brawler|berserker]
"""
import sys

import numpy as np
from PIL import Image

from . import rickmodel
from ..common import x360tex


def render(meshes, textures, view, size=(512, 768), up=2, flip_v=False):
    """meshes: rickmodel mesh dicts; textures: {name: (h, w, 4) uint8}; view: 3x3 rotation world -> camera (x right,
    y up, z towards the viewer)."""
    W, H = size
    allp = np.concatenate([m['positions'] @ view.T for m in meshes])
    lo, hi = allp.min(0), allp.max(0)
    scale = 0.92 * min(W / (hi[0] - lo[0]), H / (hi[1] - lo[1]))
    centre = (lo + hi) / 2
    img = np.full((H, W, 3), 48.0)
    zbuf = np.full((H, W), -np.inf)
    light = np.array([0.4, 0.5, 0.75])
    light /= np.linalg.norm(light)
    for m in meshes:
        p = m['positions'] @ view.T
        n = m['normals'] @ view.T
        sx = (p[:, 0] - centre[0]) * scale + W / 2
        sy = H / 2 - (p[:, 1] - centre[1]) * scale
        tex = textures.get(m['textures'].get('base'))
        uv = m['uv'] if m['uv'] is not None else np.zeros((len(p), 2))
        for a, b, c in m['triangles']:
            xs, ys = sx[[a, b, c]], sy[[a, b, c]]
            x0, x1 = int(max(0, np.floor(xs.min()))), int(min(W - 1, np.ceil(xs.max())))
            y0, y1 = int(max(0, np.floor(ys.min()))), int(min(H - 1, np.ceil(ys.max())))
            if x0 > x1 or y0 > y1:
                continue
            den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(den) < 1e-12:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            l0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
            l1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
            l2 = 1 - l0 - l1
            inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
            if not inside.any():
                continue
            z = l0 * p[a, 2] + l1 * p[b, 2] + l2 * p[c, 2]
            zb = zbuf[y0:y1 + 1, x0:x1 + 1]
            vis = inside & (z > zb)
            if not vis.any():
                continue
            nn = l0[..., None] * n[a] + l1[..., None] * n[b] + l2[..., None] * n[c]
            nn /= np.maximum(np.linalg.norm(nn, axis=-1, keepdims=True), 1e-9)
            shade = 0.35 + 0.65 * np.clip(np.abs(nn @ light), 0, 1)
            if tex is not None:
                u = l0 * uv[a, 0] + l1 * uv[b, 0] + l2 * uv[c, 0]
                v = l0 * uv[a, 1] + l1 * uv[b, 1] + l2 * uv[c, 1]
                if flip_v:
                    v = 1 - v
                th, tw = tex.shape[:2]
                tx = (np.mod(u, 1) * tw).astype(int).clip(0, tw - 1)
                ty = (np.mod(v, 1) * th).astype(int).clip(0, th - 1)
                col = tex[ty, tx].astype(float)
                vis &= col[..., 3] > 96                 # alpha-tested cards (hair)
                col = col[..., :3]
            else:
                col = np.full(gx.shape + (3,), 180.0)
            zb[vis] = z[vis]
            img[y0:y1 + 1, x0:x1 + 1][vis] = (col * shade[..., None])[vis]
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))


def views():
    """Gamebryo space (Z up, facing +X, left +Y) -> camera: front, side (his left), back."""
    front = np.array([[0, -1, 0], [0, 0, 1], [1, 0, 0]], float)    # camera looks at his face from +X
    side = np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]], float)      # from his left (+Y)
    back = np.array([[0, 1, 0], [0, 0, 1], [-1, 0, 0]], float)
    return [front, side, back]


def main(src, out, state='brawler'):
    model = rickmodel.load(src)
    skel = model.skeleton()
    meshes = [model.mesh(i, skel) for i in model.visible_meshes(state)]
    blocks = model.texture_blocks()
    names = {m['textures'].get('base') for m in meshes} - {None}
    textures = {k: x360tex.decode(blocks[k]) for k in names if k in blocks}
    shots = [render(meshes, textures, v) for v in views()]
    sheet = Image.new('RGB', (sum(s.width for s in shots), shots[0].height))
    x = 0
    for s in shots:
        sheet.paste(s, (x, 0))
        x += s.width
    sheet.save(out)
    print(out, len(meshes), 'meshes', sum(len(m['triangles']) for m in meshes), 'triangles')


if __name__ == '__main__':
    main(*sys.argv[1:])
