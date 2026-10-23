"""The NIF blocks Rick's model needs, parsed field by field (Gamebryo 2.5 / NIF 20.5.0.0, big-endian).

Every reader consumes its block exactly (check() verifies it for a whole file); fields this project does not use
are read and dropped.
"""
import struct

from . import nif

NONE = 0xFFFFFFFF


def ref(v):
    return None if v == NONE else v


# ------------------------------------------------------------------------------------------------ shared parts
def object_net(r, n, out):
    s = r.get('I')
    out['name'] = n.strings[s] if s != NONE else None
    out['extra'] = [r.get('I') for _ in range(r.get('I'))]
    out['controller'] = ref(r.get('I'))


def transform(r):
    t = r.get('3f')
    m = r.get('9f')
    s = r.get('f')
    return {'t': t, 'r': [m[0:3], m[3:6], m[6:9]], 's': s}


def av_object(r, n, out):
    object_net(r, n, out)
    out['flags'] = r.get('H')
    out.update(transform(r))
    out['properties'] = [r.get('I') for _ in range(r.get('I'))]
    out['collision'] = ref(r.get('I'))


def node(r, n, out):
    av_object(r, n, out)
    out['children'] = [ref(r.get('I')) for _ in range(r.get('I'))]
    out['effects'] = [r.get('I') for _ in range(r.get('I'))]


def switch_node(r, n, out):
    node(r, n, out)
    out['switch_flags'] = r.get('H')
    out['index'] = r.get('I')


# ------------------------------------------------------------------------------------------------ geometry
# component format 0x00CCSSTT: CC components of SS bytes each, TT the type
FMT_TYPES = {0x36: 'f', 0x37: 'f', 0x08: 'B', 0x15: 'H', 0x13: 'H', 0x21: 'I'}


def data_stream(r, n, out):
    nbytes = r.get('I')
    out['cloning'] = r.get('I')
    out['regions'] = [r.get('2I') for _ in range(r.get('I'))]
    out['formats'] = [r.get('I') for _ in range(r.get('I'))]
    out['data'] = r.d[r.p:r.p + nbytes]
    r.p += nbytes
    out['streamable'] = r.u8()


def mesh(r, n, out):
    av_object(r, n, out)
    out['materials'] = [(n.strings[r.get('I')], r.get('I')) for _ in range(r.get('I'))]
    out['active_material'] = r.get('i')
    out['material_needs_update'] = r.u8()
    out['primitive'] = r.get('I')
    out['num_submeshes'] = r.get('H')
    out['instancing'] = r.u8()
    out['bound'] = r.get('4f')
    datas = []
    for _ in range(r.get('I')):
        d = {'stream': ref(r.get('I')), 'per_instance': r.u8()}
        d['submesh_regions'] = [r.get('H') for _ in range(r.get('H'))]
        d['semantics'] = [(n.strings[r.get('I')], r.get('I')) for _ in range(r.get('I'))]
        datas.append(d)
    out['datas'] = datas
    out['modifiers'] = [ref(r.get('I')) for _ in range(r.get('I'))]


def mesh_modifier(r, n, out):
    out['submit'] = [r.get('H') for _ in range(r.get('I'))]
    out['complete'] = [r.get('H') for _ in range(r.get('I'))]


def skinning_modifier(r, n, out):
    mesh_modifier(r, n, out)
    flags = out['skin_flags'] = r.get('H')
    out['root'] = ref(r.get('I'))
    out['root_transform'] = rts(r)
    nb = r.get('I')
    out['bones'] = [ref(r.get('I')) for _ in range(nb)]
    out['bone_transforms'] = [rts(r) for _ in range(nb)]
    if flags & 2:
        out['bone_bounds'] = [r.get('4f') for _ in range(nb)]


def rts(r):
    """NiTransform as the skinning modifier stores it: rotation, translation, scale."""
    m = r.get('9f')
    t = r.get('3f')
    s = r.get('f')
    return {'r': [m[0:3], m[3:6], m[6:9]], 't': t, 's': s}


def morph_modifier(r, n, out):
    mesh_modifier(r, n, out)
    out['morph_flags'] = r.u8()
    out['num_targets'] = r.get('H')
    out['elements'] = [(n.strings[r.get('I')], r.get('I')) for _ in range(r.get('I'))]   # semantic, index
    out['unknown'] = r.get('I')


# ------------------------------------------------------------------------------------------------ materials
def _tex_map(r, shader=False):
    """A texture slot: present?, source, flags, has transform (this build stores no anisotropy)."""
    if not r.u8():
        return None
    m = {'source': ref(r.get('I')), 'map_flags': r.get('H')}
    if r.u8():
        m['transform'] = r.get('9f')        # translation(2), tiling(2), rotation, transform method, centre(2)
    if shader:
        m['map_id'] = r.get('I')
    return m


# NiTexturingProperty slots
SLOTS = ['base', 'dark', 'detail', 'gloss', 'glow', 'bump', 'normal', 'parallax', 'decal0', 'decal1']


def texturing_property(r, n, out):
    object_net(r, n, out)
    out['tex_flags'] = r.get('H')
    out['maps'] = maps = []
    for k in range(r.get('I')):
        m = _tex_map(r)
        maps.append(m)
        if m is not None and k < len(SLOTS) and SLOTS[k] == 'bump':
            m['bump'] = r.get('6f')         # luma scale, luma offset, 2x2 matrix
        if m is not None and k < len(SLOTS) and SLOTS[k] == 'parallax':
            m['offset'] = r.get('f')
    out['shader_maps'] = [_tex_map(r, True) for _ in range(r.get('I'))]


def source_texture(r, n, out):
    object_net(r, n, out)
    out['use_external'] = r.u8()
    s = r.get('I')
    out['file'] = n.strings[s] if s != NONE else None
    out['pixel_data'] = ref(r.get('I'))
    out['pixel_layout'] = r.get('I')
    out['use_mipmaps'] = r.get('I')
    out['alpha_format'] = r.get('I')
    out['is_static'] = r.u8()
    out['direct_render'] = r.u8()
    out['persist_render_data'] = r.u8()


def persistent_pixels(r, n, out):
    out['pixel_format'] = r.get('I')
    out['bits_per_pixel'] = r.u8()
    out['renderer_hint'] = r.get('i')
    out['extra'] = r.get('I')
    out['pf_flags'] = r.u8()
    out['tiling'] = r.get('I')
    out['srgb'] = r.u8()
    out['channels'] = [(r.get('I'), r.get('I'), r.u8(), r.u8()) for _ in range(4)]
    out['palette'] = ref(r.get('I'))
    nmip = r.get('I')
    out['bytes_per_pixel'] = r.get('I')
    out['hash'] = r.get('I')
    out['mips'] = [r.get('3I') for _ in range(nmip)]       # width, height, offset
    out['padded_size'] = r.get('I')                          # the Xbox 360 tiled surface, a face
    out['num_pixels'] = r.get('I')                           # bytes of the mip chain, untiled
    out['num_faces'] = r.get('I')
    out['platform'] = r.get('I')
    size = out['padded_size'] * out['num_faces']
    out['pixels'] = r.d[r.p:r.p + size]
    r.p += size


READERS = {
    'NiNode': node, 'NiSwitchNode': switch_node, 'NiMesh': mesh,
    'NiSkinningMeshModifier': skinning_modifier, 'NiMorphMeshModifier': morph_modifier,
    'NiTexturingProperty': texturing_property, 'NiSourceTexture': source_texture,
    'NiPersistentSrcTextureRendererData': persistent_pixels,
}


def reader_for(type_name):
    if type_name.startswith('NiDataStream'):
        return data_stream
    return READERS.get(type_name)


def read(n, i):
    """Block i of nif.Nif n as a dict ({'type': ...} only for types this file does not read)."""
    t = n.type_of(i)
    out = {'type': t, 'index': i}
    f = reader_for(t)
    if f is None:
        return out
    r = n.reader(i)
    f(r, n, out)
    out['_used'] = r.p - n.offsets[i]
    return out


def check(n):
    """{type: (blocks read exactly, blocks that were not)} for the types this file reads."""
    res = {}
    for i in range(len(n.block_size)):
        t = n.type_of(i)
        if reader_for(t) is None:
            continue
        ok, bad = res.get(t, (0, []))
        try:
            b = read(n, i)
            good = b['_used'] == n.block_size[i]
        except Exception as e:          # report, keep checking the others
            good = False
            b = {'_used': repr(e)}
        if good:
            ok += 1
        else:
            bad = bad + [(i, b['_used'], n.block_size[i])]
        res[t] = (ok, bad)
    return res


if __name__ == '__main__':
    import sys
    n = nif.Nif(open(sys.argv[1], 'rb').read())
    for t, (ok, bad) in sorted(check(n).items()):
        print('%-40s ok %3d  bad %3d %s' % (t, ok, len(bad), bad[:3]))
