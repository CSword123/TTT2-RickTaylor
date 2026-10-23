"""Read-only Xbox 360 disc image (XDVDFS / GDFX) reader.

The game partition starts at 0x2080000 on XGD3 discs (TTT2) and 0xFD90000 on XGD2; the volume
descriptor ("MICROSOFT*XBOX*MEDIA") is at sector 32 of it. Directories are binary trees of
entries: u16 left, u16 right (in dwords), u32 sector, u32 size, u8 attributes, u8 name length, name.
Everything is little-endian.

python -m ttt2rick.common.xdvdfs <iso> ls
python -m ttt2rick.common.xdvdfs <iso> get <path> <dest dir>
python -m ttt2rick.common.xdvdfs <iso> sha1 <path>
"""
import hashlib
import os
import struct
import sys

SECTOR = 2048
MAGIC = b'MICROSOFT*XBOX*MEDIA'
BASES = (0x2080000, 0xFD90000, 0x18300000, 0)   # XGD3, XGD2, XGD1, extracted game partition
DIRECTORY = 0x10


class Iso:
    def __init__(self, path):
        self.f = open(path, 'rb')
        for base in BASES:
            self.f.seek(base + 32 * SECTOR)
            vd = self.f.read(0x1C)
            if vd[:20] == MAGIC:
                self.base = base
                self.root, self.root_size = struct.unpack_from('<II', vd, 20)
                return
        raise ValueError('%s: no XDVDFS volume descriptor' % path)

    def read(self, sector, size):
        self.f.seek(self.base + sector * SECTOR)
        return self.f.read(size)

    def listdir(self, sector, size):
        """[(name, sector, size, is_dir)] in name order."""
        data = self.read(sector, size)
        out = []
        stack, seen = [0], set()
        while stack:
            w = stack.pop()
            off = w * 4
            if off in seen or off + 14 > len(data):
                continue
            seen.add(off)
            left, right, start, fsize, attr, nlen = struct.unpack_from('<HHIIBB', data, off)
            if left == 0xFFFF:
                continue
            out.append((data[off + 14:off + 14 + nlen].decode('latin-1'), start, fsize, bool(attr & DIRECTORY)))
            stack += [x for x in (left, right) if x]
        return sorted(out, key=lambda e: e[0].lower())

    def walk(self, sector=None, size=None, path=''):
        for name, start, fsize, is_dir in self.listdir(self.root if sector is None else sector,
                                                       self.root_size if size is None else size):
            p = path + '/' + name
            yield p, start, fsize, is_dir
            if is_dir and fsize:
                yield from self.walk(start, fsize, p)

    def lookup(self, path):
        sector, size, is_dir = self.root, self.root_size, True
        for name in [p for p in path.replace('\\', '/').split('/') if p]:
            hit = next((e for e in self.listdir(sector, size) if e[0].lower() == name.lower()), None) if is_dir else None
            if hit is None:
                raise KeyError('not found: %s' % path)
            _, sector, size, is_dir = hit
        return sector, size, is_dir

    def chunks(self, sector, size, step=1 << 24):
        for off in range(0, size, step):
            yield self.read(sector + off // SECTOR, min(step, size - off))


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    iso = Iso(argv[0])
    cmd, args = argv[1], argv[2:]
    if cmd == 'ls':
        for p, _, size, is_dir in iso.walk():
            print('%s %12d  %s' % ('d' if is_dir else '-', size, p))
    elif cmd == 'sha1':
        sector, size, _ = iso.lookup(args[0])
        h = hashlib.sha1()
        for c in iso.chunks(sector, size):
            h.update(c)
        print(h.hexdigest(), args[0])
    elif cmd == 'get':
        sector, size, is_dir = iso.lookup(args[0])
        if is_dir:
            sys.exit('give a file')
        dest = os.path.join(args[1], args[0].replace('\\', '/').rstrip('/').split('/')[-1])
        if os.path.exists(dest):
            sys.exit('%s already exists, not overwriting it' % dest)
        os.makedirs(args[1], exist_ok=True)
        with open(dest, 'wb') as f:
            for c in iso.chunks(sector, size):
                f.write(c)
        print('%10d  %s' % (size, dest))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (ValueError, KeyError, IOError) as e:
        sys.exit('xdvdfs: %s' % (e.args[0] if e.args else e))
