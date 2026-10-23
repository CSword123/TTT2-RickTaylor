"""Read-only Xbox 360 FATX ("XTAF") reader for USB storage and hard drives.

A USB stick configured by the console holds Xbox360/Data0000, Data0001, ... which together form
one device image. A hard drive (or a dd image of one) is read directly. Layout from Velocity
(hetelek/Velocity, XboxInternals/Fatx). Nothing is ever written to the source.

python -m ttt2rick.common.fatx <USB mount | Xbox360 folder | HDD image/device> ls [path]
python -m ttt2rick.common.fatx <src> find <name substring>
python -m ttt2rick.common.fatx <src> get <path> <dest dir>
python -m ttt2rick.common.fatx <src> tu [title id] <dest dir>     # title updates, default TTT2
"""
import os
import re
import struct
import sys

MAGIC = b'XTAF'
TTT2 = '4E4D0859'
ENTRY = 0x40
DELETED = 0xE5
DIRECTORY = 0x10
STFS_TITLE = 0x360   # title id in an STFS (CON/LIVE/PIRS) package header; clusters are at least 1 KiB

# (name, offset, size); size None = to the end of the device
USB = [('Content', 0x20000000, None),
       ('System Cache', 0x8000400, 0x47FF000),
       ('System Auxiliary', 0x8115200, 0x8000000),
       ('System Extended', 0x12000400, 0xDFFFC00)]
HDD = [('Content', 0x130EB0000, None),
       ('System Cache', 0x80000, 0x80000000),
       ('System Auxiliary', 0x10C080000, 0xCE30000),
       ('System Extended', 0x118EB0000, 0x8000000),
       ('System Partition', 0x120EB0000, 0x10000000)]


class Device:
    """Files concatenated into one read-only address space."""

    def __init__(self, paths):
        self.files = []
        start = 0
        for p in paths:
            f = open(p, 'rb')
            n = f.seek(0, os.SEEK_END)
            self.files.append((start, n, f))
            start += n
        self.length = start

    def read(self, off, n):
        out = bytearray()
        for start, size, f in self.files:
            if n <= 0:
                break
            if off >= start + size or off + n <= start:
                continue
            f.seek(off - start)
            chunk = f.read(min(n, start + size - off))
            if not chunk:
                break
            out += chunk
            off += len(chunk)
            n -= len(chunk)
        return bytes(out)


class Entry:
    def __init__(self, part, raw):
        self.part = part
        nlen, self.attr = raw[0], raw[1]
        self.name = raw[2:2 + min(nlen, 42)].decode('latin-1')
        self.cluster, self.size, self.created, self.written, self.accessed = struct.unpack('>5I', raw[0x2C:0x40])

    @property
    def is_dir(self):
        return bool(self.attr & DIRECTORY)

    def data(self):
        """The file's bytes, read in cluster runs."""
        out = bytearray()
        for off, n in self.part.runs(self.cluster):
            out += self.part.dev.read(off, min(n, self.size - len(out)))
            if len(out) >= self.size:
                break
        if len(out) != self.size:
            raise IOError('%s: cluster chain ends after %d of %d bytes' % (self.name, len(out), self.size))
        return bytes(out)


class Partition:
    def __init__(self, dev, name, address, size, usb):
        self.dev, self.name, self.address = dev, name, address
        self.size = dev.length - address if size is None else size
        magic, self.id, spc, self.root = struct.unpack('>4s3I', dev.read(address, 16))
        if magic != MAGIC:
            raise ValueError('no XTAF header at 0x%X' % address)
        if spc not in (2, 4, 8, 0x10, 0x20, 0x40, 0x80):
            raise ValueError('bad sectors per cluster %d' % spc)
        self.cluster_size = spc << 9
        entries = (self.size >> (self.cluster_size.bit_length() - 1)) + 1
        self.wide = (usb and name == 'Content') or entries >= 0xFFF0
        fat = ((entries << (2 if self.wide else 1)) + 0xFFF) & ~0xFFF
        if self.size - 0x1000 < fat:
            raise ValueError('too small for its FAT')
        self.clusters = (self.size - 0x1000 - fat) // self.cluster_size
        self.fat = address + 0x1000
        self.data_start = self.fat + fat

    def offset(self, cluster):
        return self.data_start + self.cluster_size * (cluster - 1)

    def chain(self, cluster):
        w = 4 if self.wide else 2
        last = 0xFFFFFFF0 if self.wide else 0xFFF0
        seen = 0
        while 0 < cluster < last:
            if cluster > self.clusters or seen > self.clusters:
                raise IOError('%s: bad cluster chain at %d' % (self.name, cluster))
            yield cluster
            seen += 1
            cluster = int.from_bytes(self.dev.read(self.fat + cluster * w, w), 'big')

    def runs(self, cluster):
        """(offset, length) of each stretch of consecutive clusters."""
        start = prev = None
        for c in self.chain(cluster):
            if prev is not None and c == prev + 1:
                prev = c
                continue
            if start is not None:
                yield self.offset(start), (prev - start + 1) * self.cluster_size
            start = prev = c
        if start is not None:
            yield self.offset(start), (prev - start + 1) * self.cluster_size

    def listdir(self, cluster=None):
        out = []
        for off, n in self.runs(self.root if cluster is None else cluster):
            raw = self.dev.read(off, n)
            for i in range(0, len(raw), ENTRY):
                e = raw[i:i + ENTRY]
                if len(e) < ENTRY or e[0] in (0, 0xFF):
                    return out
                if e[0] != DELETED:
                    out.append(Entry(self, e))
        return out

    def walk(self, cluster=None, path=''):
        for e in self.listdir(cluster):
            p = path + '/' + e.name
            yield p, e
            if e.is_dir:
                yield from self.walk(e.cluster, p)


class Drive:
    def __init__(self, src):
        if os.path.isdir(src):
            folder = os.path.join(src, 'Xbox360') if os.path.isdir(os.path.join(src, 'Xbox360')) else src
            names = sorted(n for n in os.listdir(folder) if re.fullmatch(r'Data\d{4}', n))
            if not names or names[0] != 'Data0000':
                raise ValueError('%s: no Xbox360/Data0000' % src)
            names = [n for i, n in enumerate(names) if n == 'Data%04d' % i]   # stop at the first gap
            self.dev = Device([os.path.join(folder, n) for n in names])
            self.kind, layout = 'usb', USB
        else:
            self.dev = Device([src])
            self.kind, layout = 'hdd', HDD
            major, minor, build, rev, caddr, csize = struct.unpack('>4H2I', self.dev.read(0, 16))
            if major == 2 and build >= 1525 and rev >= 1:   # newer formats store a partition table
                layout = [('Content', caddr * 0x200, csize * 0x200)] + HDD[1:]
        self.partitions = {}
        self.errors = {}
        for name, address, size in layout:
            try:
                self.partitions[name] = Partition(self.dev, name, address, size, self.kind == 'usb')
            except (ValueError, struct.error) as e:
                self.errors[name] = str(e)
        if not self.partitions:
            raise ValueError('no FATX partition found: %s' % '; '.join('%s: %s' % kv for kv in self.errors.items()))

    def walk(self):
        for name, part in self.partitions.items():
            for p, e in part.walk():
                yield name + p, e

    def lookup(self, path):
        """Entry for 'Content/0000000000000000/...' (case-insensitive), or the partition for 'Content'."""
        parts = [p for p in re.split(r'[\\/]+', path) if p]
        part = next((v for k, v in self.partitions.items() if k.lower() == parts[0].lower()), None)
        if part is None:
            raise KeyError('no partition %r (have: %s)' % (parts[0], ', '.join(self.partitions)))
        node, cluster = part, part.root
        for name in parts[1:]:
            node = next((e for e in part.listdir(cluster) if e.name.lower() == name.lower()), None)
            if node is None:
                raise KeyError('not found: %s' % path)
            cluster = node.cluster
        return node


def fat_time(v):
    """FATX timestamp (local time) as a struct for os.utime, or None."""
    import time
    y, mo, d = (v >> 25) + 1980, (v >> 21) & 15, (v >> 16) & 31
    h, mi, s = (v >> 11) & 31, (v >> 5) & 63, (v & 31) * 2
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    try:
        return time.mktime((y, mo, d, h, mi, s, 0, 0, -1))
    except (OverflowError, ValueError):
        return None


def copy(entry, dest):
    """Copy a file or a directory tree to dest (which must not exist yet)."""
    if os.path.exists(dest):
        sys.exit('%s already exists, not overwriting it' % dest)
    if entry.is_dir:
        os.makedirs(dest)
        for child in entry.part.listdir(entry.cluster):
            copy(child, os.path.join(dest, child.name))
    else:
        with open(dest, 'wb') as f:
            f.write(entry.data())
        t = fat_time(entry.written)
        if t:
            os.utime(dest, (t, t))
        print('%10d  %s' % (entry.size, dest))


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    drive = Drive(argv[0])
    cmd, args = argv[1], argv[2:]
    if cmd == 'ls':
        if not args:
            print('%s, %d MiB' % (drive.kind, drive.dev.length >> 20))
            for name, p in drive.partitions.items():
                print('%-18s 0x%010X  %6d KiB clusters  FAT%d' % (name, p.address, p.cluster_size >> 10,
                                                                 32 if p.wide else 16))
            for name, err in drive.errors.items():   # normal: content-only sticks have no system partitions
                print('%-18s absent (%s)' % (name, err))
            return
        node = drive.lookup(args[0])
        children = node.listdir() if isinstance(node, Partition) else (
            node.part.listdir(node.cluster) if node.is_dir else [node])
        for e in children:
            print('%s %12d  %s' % ('d' if e.is_dir else '-', e.size, e.name))
    elif cmd == 'find':
        for p, e in drive.walk():
            if args[0].lower() in e.name.lower():
                print('%s %12d  %s' % ('d' if e.is_dir else '-', e.size, p))
    elif cmd == 'get':
        node = drive.lookup(args[0])
        if isinstance(node, Partition):
            sys.exit('give a folder or file inside the partition')
        os.makedirs(args[1], exist_ok=True)
        copy(node, os.path.join(args[1], node.name))
    elif cmd == 'tu':
        title, dest = (args[0].upper(), args[1]) if len(args) > 1 else (TTT2, args[0])
        found = [(p, e) for p, e in drive.walk() if not e.is_dir and (
                 re.search(r'/%s/000B0000/[^/]+$' % title, p, re.I) or
                 # older dashboards keep title updates in the system cache, named TU_*: match the STFS title id
                 (re.search(r'/Cache/TU_[^/]+$', p, re.I) and e.size > STFS_TITLE + 4 and
                  e.part.dev.read(e.part.offset(e.cluster) + STFS_TITLE, 4).hex().upper() == title))]
        if not found:
            sys.exit('no title update for %s on this drive (looked in Content/0000000000000000/%s/000B0000/ '
                     'and Cache/)' % (title, title))
        os.makedirs(dest, exist_ok=True)
        for p, e in found:
            print(p)
            copy(e, os.path.join(dest, e.name))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (ValueError, KeyError, IOError) as e:
        sys.exit('fatx: %s' % (e.args[0] if e.args else e))
