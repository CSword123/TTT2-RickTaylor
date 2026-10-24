"""Havok 5.5 packfiles of Splatterhouse 2010 (Xbox 360: big-endian, 4-byte pointers), read-only: Rick's skeleton
(rick_skeleton.hkx) and his animations (hkaSplineSkeletalAnimation), decoded to per-frame local transforms.

The files are XMemCompress streams (0x0FF512ED, ttt2rick.common.xlzx) around a packfile:
    header (0x40): magic 57E0E057 10C0C010, user tag, version 5, layout rules (4 0 0 1: pointer size, little endian,
    reuse padding, empty base class), section count, contents section / offset, contents class name section /
    offset, "Havok-5.5.0-r1", flags; then per section (0x30): name (20 bytes), absolute data start, and the local
    fixups, global fixups, virtual fixups, exports, imports and end offsets (from the data start).
    local fixups {u32 src, u32 dst}: the pointer at src points to dst in the same section; global fixups {src,
    section, dst}: to dst in that section; virtual fixups {src, class name section, name offset}: an object of that
    class starts at src. Fixup tables end at 0xFFFFFFFF.
    Arrays in these classes are {pointer, i32 size} (8 bytes). hkQsTransform: translation (4 floats), rotation quaternion
    (x, y, z, w), scale (4 floats).

Members used (offsets in the objects, Havok 5.5 classes):
    hkaSkeleton (no vtable): name @0, parentIndices [i16] @4, bones [hkaBone*] @12, referencePose [hkQsTransform]
        @20. hkaBone: name @0, lockTranslation @4.
    hkaAnimationBinding: animation @8, transformTrackToBoneIndices hkArray<i16> @12, ...
    hkaSkeletalAnimation: type @8, duration @12, numberOfTracks @16, extractedMotion @20, annotationTracks @24.
    hkaSplineSkeletalAnimation: numFrames @36, numBlocks @40, maxFramesPerBlock @44, maskAndQuantizationSize @48,
        blockDuration @52, blockInverseDuration @56, frameDuration @60, blockOffsets hkArray<u32> @64,
        floatBlockOffsets @76, transformOffsets @88, floatOffsets @100, data hkArray<u8> @112, endian @124.
    (These offsets are checked against the fixups when a file is read: each array member must hold a pointer.)

python3 -m ttt2rick.splatterhouse.hkx <file.hkx> [anim]     # what the file holds; with anim, track summaries
"""
import math
import struct
import sys

import numpy as np

from ..common import xlzx

MAGIC = (0x57E0E057, 0x10C0C010)


class Packfile:
    def __init__(self, raw):
        d = xlzx.read_file(raw) if raw[:4] == bytes.fromhex('0ff512ed') else raw
        if struct.unpack_from('>II', d, 0) != MAGIC:
            raise ValueError('not a Havok packfile')
        self.d = d
        nsec, = struct.unpack_from('>i', d, 0x14)
        self.sections = []
        for s in range(nsec):
            o = 0x40 + 0x30 * s
            name = d[o:o + 20].split(b'\0')[0].decode()
            start, local, glob, virt, exports, imports, end = struct.unpack_from('>7I', d, o + 20)
            self.sections.append(dict(name=name, start=start, local=local, glob=glob, virt=virt, exports=exports,
                                      end=end))
        self.pointers = {}            # absolute address of a pointer -> absolute address it points to
        self.objects = []             # (absolute address, class name)
        for s in self.sections:
            base = s['start']
            for k in range(s['local'], s['glob'] - 7, 8):
                src, dst = struct.unpack_from('>II', d, base + k)
                if src != 0xFFFFFFFF:
                    self.pointers[base + src] = base + dst
            for k in range(s['glob'], s['virt'] - 11, 12):
                src, sec, dst = struct.unpack_from('>III', d, base + k)
                if src != 0xFFFFFFFF:
                    self.pointers[base + src] = self.sections[sec]['start'] + dst
            for k in range(s['virt'], s['exports'] - 11, 12):
                src, sec, name = struct.unpack_from('>III', d, base + k)
                if src != 0xFFFFFFFF:
                    self.objects.append((base + src, self.cstr(self.sections[sec]['start'] + name)))

    def cstr(self, a):
        return self.d[a:self.d.index(b'\0', a)].decode('latin1')

    def of_class(self, name):
        return [a for a, c in self.objects if c == name]

    def ptr(self, a):
        return self.pointers.get(a)

    def u32(self, a):
        return struct.unpack_from('>I', self.d, a)[0]

    def i32(self, a):
        return struct.unpack_from('>i', self.d, a)[0]

    def f32(self, a):
        return struct.unpack_from('>f', self.d, a)[0]

    def array(self, a):
        """(address of the first item or None, size) of the hkArray at a."""
        n = self.i32(a + 4)
        p = self.ptr(a)
        if n and p is None:
            raise ValueError('hkArray at %x: %d items but no pointer (wrong member offset?)' % (a, n))
        return p, n

    def string(self, a):
        p = self.ptr(a)
        return self.cstr(p) if p is not None else None


def skeleton(pf):
    """{names, parents, reference (n, 10): tx ty tz qx qy qz qw sx sy sz} of the file's hkaSkeleton."""
    a = pf.of_class('hkaSkeleton')[0]
    pp, n = pf.array(a + 4)
    parents = list(struct.unpack_from('>%dh' % n, pf.d, pp)) if n else []
    bp, nb = pf.array(a + 12)
    names = [pf.string(pf.ptr(bp + 4 * k)) for k in range(nb)]
    rp, nr = pf.array(a + 20)
    ref = np.array([struct.unpack_from('>12f', pf.d, rp + 48 * k) for k in range(nr)])
    ref = np.concatenate([ref[:, 0:3], ref[:, 4:8], ref[:, 8:11]], 1)
    return dict(name=pf.string(a), names=names, parents=parents, reference=ref)
