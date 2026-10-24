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


# ------------------------------------------------------------------------------------------------ spline animations
# Block data (hkaSplineSkeletalAnimation.data at blockOffsets[b]): first a 4-byte mask per transform track
# {quantization, position, rotation, scale}: quantization bits 0-1 position (0: 8 bits, 1: 16 bits), 2-5 rotation
# (ROT_SIZE), 6-7 scale; position / scale bits 0-2 static x y z, 4-6 spline x y z; rotation bits 0-3 static, 4-7
# spline (any: the whole quaternion). Then per track its position, rotation and scale data:
# The block data has its own byte order (the animation's endian @124: 0 little, as in these files).
#   spline: u16 items, u8 degree, (items + degree + 2) u8 knots (frames in the block); then (vectors) align 4, per
#   axis min and max floats for spline axes, one float for static ones, (items + 1) control points of the spline
#   axes' quantized values, align 4; (rotations) align to the quantization's alignment, (items + 1) quaternions.
#   static only: vectors one float per static axis; rotations one quaternion. Rotations end aligned to 4.
# A value is the B-spline of its control points at the frame's time in the block (knots in frames); quaternions are
# normalized afterwards.
ROT_SIZE = {0: 4, 1: 5, 2: 6, 3: 3, 4: 2, 5: 16}          # POLAR32, THREECOMP40, THREECOMP48, THREECOMP24, STRAT16, raw
ROT_ALIGN = {0: 4, 1: 1, 2: 2, 3: 1, 4: 2, 5: 4}


def quat40(b):
    """THREECOMP40: 40 bits, little-endian: three 12-bit components (each (v - 2047) / (2047 sqrt 2)), 2 bits the
    index of the component left out (the largest), 1 bit its sign."""
    v = int.from_bytes(b[:5], 'little')
    c = [((v >> (12 * k)) & 0xFFF) - 2047 for k in range(3)]
    c = [x * 0.000345436 for x in c]
    w = math.sqrt(max(0.0, 1.0 - sum(x * x for x in c)))
    if (v >> 38) & 1:
        w = -w
    c.insert((v >> 36) & 3, w)
    return c


def find_span(n, p, u, knots):
    if u >= knots[n + 1]:
        return n
    lo, hi = p, n + 1
    mid = (lo + hi) // 2
    while u < knots[mid] or u >= knots[mid + 1]:
        if u < knots[mid]:
            hi = mid
        else:
            lo = mid
        mid = (lo + hi) // 2
    return mid


def bspline(points, p, knots, u):
    """The B-spline (degree p, knots, control points (n + 1, k)) at u."""
    n = len(points) - 1
    if n == 0:
        return points[0]
    span = find_span(n, p, u, knots)
    N = [1.0] + [0.0] * p
    left, right = [0.0] * (p + 1), [0.0] * (p + 1)
    for j in range(1, p + 1):
        left[j] = u - knots[span + 1 - j]
        right[j] = knots[span + j] - u
        saved = 0.0
        for r in range(j):
            den = right[r + 1] + left[j - r]
            t = N[r] / den if den else 0.0
            N[r] = saved + right[r + 1] * t
            saved = left[j - r] * t
        N[j] = saved
    out = np.zeros(points.shape[1])
    for i in range(p + 1):
        out += N[i] * points[span - p + i]
    return out


class _Reader:
    def __init__(self, d, pos, endian='<'):
        self.d, self.pos, self.start, self.e = d, pos, pos, endian

    def align(self, n):
        self.pos += -(self.pos - self.start) % n

    def u8(self):
        self.pos += 1
        return self.d[self.pos - 1]

    def u16(self):
        self.pos += 2
        return struct.unpack_from(self.e + 'H', self.d, self.pos - 2)[0]

    def f32(self):
        self.pos += 4
        return struct.unpack_from(self.e + 'f', self.d, self.pos - 4)[0]

    def take(self, n):
        self.pos += n
        return self.d[self.pos - n:self.pos]


def _spline_header(r):
    items, degree = r.u16(), r.u8()
    knots = list(r.take(items + degree + 2))
    return items, degree, knots


def _vector(r, mask, quant, default):
    """A track's position or scale: (function of block time) -> 3 floats."""
    static = [bool(mask & (1 << k)) for k in range(3)]
    spline = [bool(mask & (0x10 << k)) for k in range(3)]
    if any(spline):
        items, degree, knots = _spline_header(r)
        r.align(4)
        lo, hi, value = [0.0] * 3, [0.0] * 3, list(default)
        for k in range(3):
            if spline[k]:
                lo[k], hi[k] = r.f32(), r.f32()
            elif static[k]:
                value[k] = r.f32()
        pts = np.tile(np.array(value, float), (items + 1, 1))
        size = 2 if quant else 1
        top = 65535.0 if quant else 255.0
        for i in range(items + 1):
            for k in range(3):
                if spline[k]:
                    q = r.u16() if quant else r.u8()
                    pts[i, k] = lo[k] + (hi[k] - lo[k]) * q / top
        r.align(4)
        return lambda u: bspline(pts, degree, knots, u)
    value = list(default)
    for k in range(3):
        if static[k]:
            value[k] = r.f32()
    value = np.array(value, float)
    return lambda u: value


def _rotation(r, mask, quant):
    if quant not in (1,):
        raise NotImplementedError('rotation quantization %d' % quant)
    if mask & 0xF0:
        items, degree, knots = _spline_header(r)
        r.align(ROT_ALIGN[quant])
        pts = np.array([quat40(r.take(5)) for _ in range(items + 1)], float)
        for i in range(1, len(pts)):              # the same hemisphere as the previous control point
            if np.dot(pts[i], pts[i - 1]) < 0:
                pts[i] = -pts[i]
        r.align(4)

        def f(u):
            q = bspline(pts, degree, knots, u)
            return q / np.linalg.norm(q)
        return f
    if mask & 0x0F:
        r.align(ROT_ALIGN[quant])
        q = np.array(quat40(r.take(5)), float)
        r.align(4)
        return lambda u: q
    return lambda u: np.array([0.0, 0.0, 0.0, 1.0])


def animation(pf):
    """{frames, fps, tracks: (frames, tracks, 10) tx ty tz qx qy qz qw sx sy sz, bones: track -> skeleton bone}
    of the file's (first) hkaSplineSkeletalAnimation and its binding."""
    a = pf.of_class('hkaSplineSkeletalAnimation')[0]
    ntracks, frames = pf.i32(a + 16), pf.i32(a + 36)
    per_block = pf.i32(a + 44)
    frame_time = pf.f32(a + 60)
    bo, nb = pf.array(a + 64)
    dp, _ = pf.array(a + 112)
    out = np.zeros((frames, ntracks, 10))
    for b in range(nb):
        r = _Reader(pf.d, dp + pf.u32(bo + 4 * b), '<' if pf.u32(a + 124) == 0 else '>')
        masks = [tuple(r.take(4)) for _ in range(ntracks)]
        r.align(4)
        fns = []
        for q, pm, rm, sm in masks:
            pos = _vector(r, pm, q & 3, (0.0, 0.0, 0.0))
            rot = _rotation(r, rm, (q >> 2) & 15)
            scl = _vector(r, sm, (q >> 6) & 3, (1.0, 1.0, 1.0))
            fns.append((pos, rot, scl))
        first = b * (per_block - 1)
        for f in range(first, min(frames, first + per_block)):
            u = float(f - first)
            for t, (pos, rot, scl) in enumerate(fns):
                out[f, t] = np.concatenate([pos(u), rot(u), scl(u)])
    bones = list(range(ntracks))
    for bind in pf.of_class('hkaAnimationBinding'):
        if pf.ptr(bind) == a:
            ip, n = pf.array(bind + 4)
            if n:
                bones = list(struct.unpack_from('>%dh' % n, pf.d, ip))
    return dict(frames=frames, fps=1.0 / frame_time if frame_time else 30.0, tracks=out, bones=bones)


def main(argv):
    pf = Packfile(open(argv[0], 'rb').read())
    print(sorted(set(c for _, c in pf.objects)))
    if pf.of_class('hkaSkeleton'):
        s = skeleton(pf)
        print('skeleton %s: %d bones' % (s['name'], len(s['names'])))
    if len(argv) > 1 and pf.of_class('hkaSplineSkeletalAnimation'):
        an = animation(pf)
        q = an['tracks'][..., 3:7]
        print('%d frames at %.0f fps, %d tracks; |q| %.4f..%.4f' % (an['frames'], an['fps'], q.shape[1],
              np.linalg.norm(q, axis=-1).min(), np.linalg.norm(q, axis=-1).max()))


if __name__ == '__main__':
    main(sys.argv[1:])
