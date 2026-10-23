"""TTT2 (Xbox 360) data archives, read-only, from an installed game folder (TTT2-Recomp's `game\\`).

nrfo.bin: u32 count, then (u32 offset, u32 size) per archive record; record i indexes the i-th dataNNN.bin in name
order. A record (like an update's dataNNN.ofs) is a list of boxes {u32 size, char[4] kind, payload}, big-endian:
`ofsi` holds one (u32 key, u32 word) per entry and `ofsd` one u32 offset per entry plus the end, into the archive's
payload at 0x100. Entries are 16-byte aligned; an offset's low four bits are the entry's length modulo 16 (0: a
multiple of 16). Unlike the Wii U port, entries are stored as they are (no scrambling, no NRCZ).

Keys: the CRC-32 of the name with the register starting at zero (`zlib.crc32(name, 0xFFFFFFFF)`), e.g. `mar.nud`.
Members of a pack continue that CRC over the member index's base-4 digits, least significant first, one byte each.
The update's archives (`update\\data100.ofs` + `.bin`) are loaded last and win; when ttt2rick.ttt2.overlay has changed
them, this reads the title update's own copies in `update\\original` instead. Format and naming as in Petexy's Wii U
port (third_party/petexy-ttt2, tools/characters/ttt2char/ttt2/archive.py).

python -m ttt2rick.ttt2.archive <game folder> find <name>...       # where each name's entry is
python -m ttt2rick.ttt2.archive <game folder> get <dest> <name>...  # extract by name (or by 8-digit hex key)
python -m ttt2rick.ttt2.archive <game folder> stats                  # entries and leading magics per archive
"""
import collections
import os
import re
import struct
import sys
import zlib

PAYLOAD = 0x100


def key_of(name):
    return zlib.crc32(name.encode('latin1'), 0xFFFFFFFF)


def member_key(pack, index):
    digits = bytearray()
    while index:
        digits.append(index & 3)
        index >>= 2
    return zlib.crc32(bytes(digits), pack) if digits else pack


def boxes(d):
    out, pos = {}, 0
    while pos + 8 <= len(d):
        size, kind = struct.unpack_from('>I4s', d, pos)
        if size < 8 or pos + size > len(d):
            break
        out.setdefault(kind, (pos + 8, size - 8))
        pos += size
    return out


def parse_index(rec):
    """[(key, word, offset in the payload, size)] of an archive record."""
    b = boxes(rec)
    if b'ofsi' not in b or b'ofsd' not in b:
        raise ValueError('not an archive index')
    (pi, si), (po, so) = b[b'ofsi'], b[b'ofsd']
    keys = [struct.unpack_from('>II', rec, pi + 8 * i) for i in range(si // 8)]
    offsets = struct.unpack_from('>%dI' % (so // 4), rec, po)
    if len(offsets) != len(keys) + 1:
        raise ValueError('archive index tables disagree')
    out = []
    for i, (key, word) in enumerate(keys):
        start, end, tail = offsets[i] & ~0xF, offsets[i + 1] & ~0xF, offsets[i] & 0xF
        size = end - start if tail == 0 else max(end - start, 16) - 16 + tail
        out.append((key, word, start, size))
    return out


class Archives:
    def __init__(self, game):
        if os.path.isdir(os.path.join(game, 'game')):
            game = os.path.join(game, 'game')
        nrfo = open(os.path.join(game, 'nrfo.bin'), 'rb').read()
        names = sorted(n for n in os.listdir(game) if re.fullmatch(r'data\d{3}\.bin', n))
        count, = struct.unpack_from('>I', nrfo)
        if count != len(names):
            raise ValueError('nrfo.bin has %d archives, %s has %d dataNNN.bin' % (count, game, len(names)))
        self.paths, self.indices = {}, {}
        for i, n in enumerate(names):
            off, size = struct.unpack_from('>II', nrfo, 4 + 8 * i)
            self.paths[n] = os.path.join(game, n)
            self.indices[n] = parse_index(nrfo[off:off + size])
        update = os.path.join(game, 'update')
        if os.path.isdir(os.path.join(update, 'original')):     # ttt2rick.ttt2.overlay's changes: read the game's own
            update = os.path.join(update, 'original')
        for n in sorted(os.listdir(update)) if os.path.isdir(update) else []:
            if re.fullmatch(r'data\d{3}\.ofs', n):
                b = n[:-4] + '.bin'
                self.paths['update/' + b] = os.path.join(update, b)
                self.indices['update/' + b] = parse_index(open(os.path.join(update, n), 'rb').read())
        self.where = {}               # key -> (archive, index); the last one loaded (the update) wins
        for a, entries in self.indices.items():
            for i, e in enumerate(entries):
                self.where[e[0]] = (a, i)
        self._files = {}

    def entry(self, archive, index):
        _, _, start, size = self.indices[archive][index]
        f = self._files.get(archive)
        if f is None:
            f = self._files[archive] = open(self.paths[archive], 'rb')
        f.seek(PAYLOAD + start)
        data = f.read(size)
        if len(data) != size:
            raise IOError('%s entry %d: archive ends early' % (archive, index))
        return data

    def has(self, key):
        return key in self.where

    def read(self, key):
        if key not in self.where:
            raise KeyError('the game has no archive entry %08x' % key)
        return self.entry(*self.where[key])

    def read_name(self, name):
        return self.read(key_of(name))


def _key(name):
    return int(name, 16) if re.fullmatch(r'[0-9a-fA-F]{8}', name) else key_of(name)


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    arc = Archives(argv[0])
    cmd, args = argv[1], argv[2:]
    if cmd == 'find':
        for name in args:
            k = _key(name)
            if k in arc.where:
                a, i = arc.where[k]
                print('%08x %-14s %-20s #%d  %d bytes' % (k, name, a, i, arc.indices[a][i][3]))
            else:
                print('%08x %-14s -' % (k, name))
    elif cmd == 'get':
        dest = args[0]
        os.makedirs(dest, exist_ok=True)
        for name in args[1:]:
            data = arc.read(_key(name))
            path = os.path.join(dest, name)
            open(path, 'wb').write(data)
            print('%10d  %s' % (len(data), path))
    elif cmd == 'stats':
        for a, entries in arc.indices.items():
            magic = collections.Counter()
            for i in range(len(entries)):
                f = arc._files.get(a) or open(arc.paths[a], 'rb')
                arc._files[a] = f
                f.seek(PAYLOAD + entries[i][2])
                m = f.read(4)
                magic[m.decode() if m.isalnum() else m.hex()] += 1
            print('%-20s %5d  %s' % (a, len(entries), ' '.join('%s:%d' % kv for kv in magic.most_common(5))))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (ValueError, KeyError, IOError) as e:
        sys.exit('archive: %s' % (e.args[0] if e.args else e))
