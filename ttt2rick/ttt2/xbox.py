"""TTT2's Xbox 360 models, textures and skeletons, through the Wii U readers in ttt2rick.ttt2.petexy.

- NUD: "NDXR" instead of "NDP3"; the rest is the same big-endian layout, byte for byte.
- NUT: "NTXR" instead of "NTP3"; same headers. The mips are linear (not tiled) but stored as big-endian 16-bit words,
  so every byte pair is swapped against the PC/Wii U block order. read_nut swaps them, write_nut swaps them back.
  (Only the block formats 0 BC1 / 1 BC2 / 2 BC3 are checked so far.)
- BONE: identical (little-endian, as on Wii U).
"""
import numpy as np

from .petexy import bone, nud, nut


def swap16(b):
    return np.frombuffer(b, np.uint8).reshape(-1, 2)[:, ::-1].tobytes()


def read_nud(d):
    if d[:4] != b'NDXR':
        raise ValueError('not an Xbox 360 NUD (NDXR)')
    return nud.read(b'NDP3' + d[4:])


def write_nud(model):
    return b'NDXR' + nud.write(model)[4:]


def read_nut(d):
    if d[:4] != b'NTXR':
        raise ValueError('not an Xbox 360 NUT (NTXR)')
    n = nut.read(b'NTP3' + d[4:])
    for t in n['textures']:
        t['mips'] = [swap16(m) for m in t['mips']]
    return n


def write_nut(n):
    swapped = dict(n, textures=[dict(t, mips=[swap16(m) for m in t['mips']]) for t in n['textures']])
    return b'NTXR' + nut.write(swapped)[4:]


def decode_texture(t):
    """(h, w, 4) uint8 RGBA of a read_nut texture's top mip."""
    return nut.decode(t)


read_bone = bone.read
write_bone = bone.write
