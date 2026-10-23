"""Rick's model out of rick.nif: skeleton (bind pose), the meshes of a costume state with their skin weights, and
the textures they use.

Gamebryo conventions as this file uses them (checked by bind_error()): a node's rotation is stored row-major and
applies to column vectors (world = parent_R @ R, parent_R @ (s * t) + parent_t), units are metres, Z up, the
fighter facing +X with his left at +Y. A skinned vertex v of a mesh lands at bone_world @ bone_transform @ v for
each bone it is weighted to, and the file's rest pose is the bind pose (an A-pose).
"""
import numpy as np

from . import nif
from . import nifblocks as nb

# the switch children shown for each costume state (switch name -> child name); switches not listed keep the
# file's own index
STATES = {
    'brawler': {'rick_visibility_switch': 'show', 'C_torso_switch': 'Brawler_Rick',
                'C_stomachGore_switch': 'torso_geo', 'C_neckGore_switch': 'head',
                'R_FlankDmg': 'R_FlankDmgExt', 'L_FlankDmg': 'L_FlankDmgExt', 'R_ShldrDmg': 'R_ShldrDmgExt',
                'L_Arm': 'L_ArmDmg_off'},
    'berserker': {'rick_visibility_switch': 'show', 'C_torso_switch': 'Berserker_rick',
                  'R_longClaw': 'R_longClaw_on', 'L_longClaw': 'L_longClaw_on'},
}
# groups that only show while the left arm grows back (Splatterhouse's limb regeneration)
REGEN_GROUPS = {'L_arm_regen_geo'}

COMPONENT_DTYPE = {0x35: '>f4', 0x36: '>f4', 0x37: '>f4', 0x08: 'u1', 0x15: '>u2', 0x13: '>u2', 0x21: '>u4'}


def fmt_info(f):
    """(components, bytes per component, numpy dtype) of a component format 0x00CCSSTT."""
    count, size, kind = (f >> 16) & 0xFF, (f >> 8) & 0xFF, f & 0xFF
    dt = COMPONENT_DTYPE.get(kind)
    if dt is None or np.dtype(dt).itemsize != size:
        raise ValueError('unknown component format %08x' % f)
    return count, size, dt


def local_matrix(b):
    m = np.eye(4)
    m[:3, :3] = np.array(b['r']) * b['s']
    m[:3, 3] = b['t']
    return m


class Model:
    def __init__(self, data):
        self.nif = n = nif.Nif(data)
        self.blocks = B = {i: nb.read(n, i) for i in range(len(n.block_size))}
        self.parent = {}
        for i, b in B.items():
            for c in b.get('children', []):
                if c is not None:
                    self.parent[c] = i
        self.by_name = {}
        for i, b in B.items():
            if b.get('name') and 'children' in b:
                self.by_name.setdefault(b['name'], i)
        self.world = {}
        for i, b in B.items():
            if 'children' in b or b['type'] == 'NiMesh':
                self.world_of(i)

    def world_of(self, i):
        if i not in self.world:
            m = local_matrix(self.blocks[i])
            p = self.parent.get(i)
            self.world[i] = self.world_of(p) @ m if p is not None else m
        return self.world[i]

    # -------------------------------------------------------------------------------------- skeleton
    def skeleton(self):
        """Joints from root_jnt down: {'names', 'parents', 'world' (n, 4, 4)} in Gamebryo space."""
        root = self.by_name['root_jnt']
        names, parents, world, index = [], [], [], {}
        todo = [(root, -1)]
        while todo:
            i, p = todo.pop(0)
            b = self.blocks[i]
            index[i] = len(names)
            names.append(b['name'])
            parents.append(p)
            world.append(self.world_of(i))
            todo += [(c, index[i]) for c in b['children']
                     if c is not None and self.blocks[c]['type'] == 'NiNode']
        return {'names': names, 'parents': parents, 'world': np.array(world), 'block': index}

    # -------------------------------------------------------------------------------------- visibility
    def visible_meshes(self, state='brawler', regen=False):
        """Mesh block indices drawn in a costume state."""
        choose = STATES[state]
        root = 0
        out = []
        todo = [(root, False)]
        while todo:
            i, chosen = todo.pop()
            b = self.blocks[i]
            # a switch's chosen child is shown whatever its own hidden bit (the game sets it when it switches:
            # Berserker_rick is stored hidden)
            hidden = b.get('flags', 0) & 1 and not chosen
            if b['type'] == 'NiMesh':
                if not hidden:
                    out.append(i)
                continue
            if 'children' not in b or hidden:
                continue
            if b.get('name') in REGEN_GROUPS and not regen:
                continue
            kids = [c for c in b['children'] if c is not None]
            if b['type'] == 'NiSwitchNode':
                names = [self.blocks[c].get('name') for c in b['children']]
                want = choose.get(b['name'])
                k = names.index(want) if want in names else b['index']
                if b['children'][k] is not None:
                    todo.append((b['children'][k], True))
                continue
            todo += [(c, False) for c in kids]
        return sorted(out)

    # -------------------------------------------------------------------------------------- geometry
    def streams(self, mi):
        """{(semantic, index): array (elements, components)} of mesh block mi, plus ('_regions', semantic): the
        (start, count) of each submesh in that semantic's stream. A submesh's indices count from the start of its
        vertex region, and its BLENDINDICES index its own BONE_PALETTE region."""
        m = self.blocks[mi]
        out = {}
        for d in m['datas']:
            s = self.blocks[d['stream']]
            infos = [fmt_info(f) for f in s['formats']]
            stride = sum(c * z for c, z, _ in infos)
            nvert = len(s['data']) // stride
            raw = np.frombuffer(s['data'], np.uint8)[:nvert * stride].reshape(nvert, stride)
            off = 0
            for (name, idx), (c, z, dt) in zip(d['semantics'], infos):
                col = raw[:, off:off + c * z].copy().view(dt).reshape(nvert, c)
                out[(name, idx)] = col.astype(np.float64 if dt.endswith('f4') else np.int64)
                off += c * z
            regions = [s['regions'][k] for k in d['submesh_regions']]
            for name, _ in d['semantics']:
                out[('_regions', name)] = regions
        return out

    def triangles(self, st):
        """(triangles, 3) vertex indices over the whole vertex stream."""
        idx = st[('INDEX', 0)].reshape(-1)
        vreg = st[('_regions', 'POSITION_BP' if ('POSITION_BP', 0) in st else 'POSITION')]
        tris = []
        for (s, c), (vs, _) in zip(st[('_regions', 'INDEX')], vreg):
            tris.append(idx[s:s + c].reshape(-1, 3) + vs)
        return np.concatenate(tris)

    def skin(self, mi):
        """The skinning modifier of mesh mi (None if it has none)."""
        for k in self.blocks[mi]['modifiers']:
            if k is not None and self.blocks[k]['type'] == 'NiSkinningMeshModifier':
                return self.blocks[k]
        return None

    def mesh(self, mi, skel):
        """One mesh in the bind pose: {'name', 'positions', 'normals', 'uv', 'triangles', 'joints' (v, 4) skeleton
        indices, 'weights' (v, 4), 'textures' {slot: texture name}, 'material'}."""
        m = self.blocks[mi]
        st = self.streams(mi)
        pos = st.get(('POSITION_BP', 0), st.get(('POSITION', 0)))
        nrm = st.get(('NORMAL_BP', 0), st.get(('NORMAL', 0)))
        uv = st.get(('TEXCOORD', 0))
        tri = self.triangles(st)
        sk = self.skin(mi)
        nv = len(pos)
        joints = np.zeros((nv, 4), np.int64)
        weights = np.zeros((nv, 4))
        if sk is not None:
            bi = st[('BLENDINDICES', 0)]
            bw = st[('BLENDWEIGHT', 0)]
            w = np.zeros((nv, 4))
            w[:, :bw.shape[1]] = bw
            if bw.shape[1] == 3:
                w[:, 3] = np.clip(1.0 - bw.sum(1), 0, 1)
            palette = st.get(('BONE_PALETTE', 0))
            local = bi.copy()
            if palette is not None:
                pal = palette.reshape(-1)
                for (vs, vc), (ps, _) in zip(st[('_regions', 'BLENDINDICES')], st[('_regions', 'BONE_PALETTE')]):
                    local[vs:vs + vc] = pal[ps + bi[vs:vs + vc]]
            bone_skel = np.array([skel['block'].get(b, -1) for b in sk['bones']])
            joints = bone_skel[local]
            weights = w
            # move bind-pose vertices to world through each weighted bone (the rest pose); they agree when the
            # rest pose is the bind pose (bind_error)
            world = np.zeros((nv, 3))
            wn = np.zeros((nv, 3))
            for k in range(4):
                for b in np.unique(local[:, k]):
                    sel = local[:, k] == b
                    M = self.world_of(sk['bones'][b]) @ local_matrix(sk['bone_transforms'][b])
                    world[sel] += weights[sel, k:k + 1] * (pos[sel] @ M[:3, :3].T + M[:3, 3])
                    wn[sel] += weights[sel, k:k + 1] * (nrm[sel] @ M[:3, :3].T)
            pos_w = world
            nrm_w = wn / np.maximum(np.linalg.norm(wn, axis=1, keepdims=True), 1e-9)
        else:
            M = self.world_of(mi)
            pos_w = pos @ M[:3, :3].T + M[:3, 3]
            nrm_w = nrm @ M[:3, :3].T
            p = self.parent.get(mi)
            while p is not None and self.blocks[p]['name'] not in skel['names']:
                p = self.parent.get(p)
            joints[:, 0] = skel['names'].index(self.blocks[p]['name']) if p is not None else 0
            weights[:, 0] = 1.0
        return {'name': m['name'], 'block': mi, 'positions': pos_w, 'normals': nrm_w, 'uv': uv,
                'triangles': tri, 'joints': joints, 'weights': weights, 'textures': self.textures_of(mi),
                'material': m['materials'][m['active_material']][0] if m['materials'] else None}

    def bind_error(self, mi):
        """Largest distance (m) between a vertex placed through its different weighted bones: 0 when the nodes'
        rest pose is the skin's bind pose."""
        sk = self.skin(mi)
        if sk is None:
            return 0.0
        st = self.streams(mi)
        pos = st.get(('POSITION_BP', 0), st.get(('POSITION', 0)))
        Ms = [self.world_of(b) @ local_matrix(t) for b, t in zip(sk['bones'], sk['bone_transforms'])]
        P = np.array([pos @ M[:3, :3].T + M[:3, 3] for M in Ms])
        return float(np.abs(P - P[0]).max())

    # -------------------------------------------------------------------------------------- materials
    def textures_of(self, mi):
        out = {}
        for p in self.blocks[mi]['properties']:
            b = self.blocks[p]
            if b['type'] == 'NiTexturingProperty':
                for k, mp in enumerate(b['maps']):
                    if mp and mp['source'] is not None:
                        out[nb.SLOTS[k]] = self.blocks[mp['source']]['file']
        return out

    def texture_blocks(self):
        """{texture file name: NiPersistentSrcTextureRendererData block}."""
        out = {}
        for b in self.blocks.values():
            if b['type'] == 'NiSourceTexture' and b['pixel_data'] is not None:
                out[b['file']] = self.blocks[b['pixel_data']]
        return out


def load(path):
    from ..common import xlzx
    return Model(xlzx.read_file(open(path, 'rb').read()))
