"""Gamebryo 20.5 NIF files as Splatterhouse (2010, Bottle Rocket) writes them for the Xbox 360: the header and the
raw bytes of each block. The version, user version and block count are little-endian; everything after them is
big-endian (endian byte 0).
"""
import struct
import sys


class Reader:
    def __init__(self, data, p=0, endian='>'):
        self.d = data
        self.p = p
        self.e = endian

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def get(self, fmt):
        v = struct.unpack_from(self.e + fmt, self.d, self.p)
        self.p += struct.calcsize(self.e + fmt)
        return v if len(v) > 1 else v[0]

    def string(self):
        n = self.get('I')
        s = self.d[self.p:self.p + n].decode('latin-1')
        self.p += n
        return s


class Nif:
    def __init__(self, data):
        self.data = data
        nl = data.index(b'\n')
        self.banner = data[:nl].decode('latin-1')
        p = nl + 1
        self.version, = struct.unpack_from('<I', data, p)
        p += 4
        endian = data[p]
        p += 1
        # the user version and the block count stay little-endian; the endian byte applies from the type table on
        self.user_version, n = struct.unpack_from('<II', data, p)
        r = Reader(data, p + 8, '<' if endian else '>')
        # Bottle Rocket's "BR Version" header has no export info strings (checked against the block sizes)
        ntypes = r.get('H')
        self.types = [r.string() for _ in range(ntypes)]
        self.block_type = [r.get('H') & 0x7FFF for _ in range(n)]
        self.block_size = [r.get('I') for _ in range(n)]
        nstr = r.get('I')
        r.get('I')                          # longest string
        self.strings = [r.string() for _ in range(nstr)]
        ngroups = r.get('I')
        self.groups = [r.get('I') for _ in range(ngroups)]
        self.header_end = r.p
        self.offsets = []
        q = r.p
        for s in self.block_size:
            self.offsets.append(q)
            q += s
        self.end = q
        self.r = r

    def type_of(self, i):
        return self.types[self.block_type[i]]

    def block(self, i):
        o = self.offsets[i]
        return self.data[o:o + self.block_size[i]]

    def reader(self, i):
        return Reader(self.data, self.offsets[i], self.r.e)


if __name__ == '__main__':
    nif = Nif(open(sys.argv[1], 'rb').read())
    print(nif.banner, hex(nif.version), 'user', nif.user_version)
    print('%d blocks, %d types, %d strings, header %d, blocks end %d, file %d' % (
        len(nif.block_size), len(nif.types), len(nif.strings), nif.header_end, nif.end, len(nif.data)))
    from collections import Counter
    c = Counter(nif.type_of(i) for i in range(len(nif.block_size)))
    for t, k in c.most_common():
        print('  %4d %s' % (k, t))
