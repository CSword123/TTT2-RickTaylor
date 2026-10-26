"""Put files into an installed game's update archive (`game/update/data100.ofs` + `.bin`), which the game loads after
the disc's archives, so an entry here replaces the disc's entry with the same key. The stock recomp build needs no
patch for this.

The first install copies the title update's own data100.ofs/.bin to `update/original/`; every install starts again
from those, so installing twice does not stack, and `restore` puts them back.

python -m ttt2rick.ttt2.overlay <game folder> install <dir> [<dir> ...]    # each file in each <dir> under the key
                                                                          of its name (key_XXXXXXXX.bin: that key);
                                                                          a later <dir>'s file wins over an earlier's
python -m ttt2rick.ttt2.overlay <game folder> restore
python -m ttt2rick.ttt2.overlay <game folder> list
"""
import os
import re
import shutil
import struct
import sys

from .archive import PAYLOAD, boxes, key_of, parse_index

NAMES = ('data100.ofs', 'data100.bin')


def _box(kind, payload):
    return struct.pack('>I4s', 8 + len(payload), kind) + payload


def _update_dir(game):
    if os.path.isdir(os.path.join(game, 'game')):
        game = os.path.join(game, 'game')
    update = os.path.join(game, 'update')
    if not all(os.path.isfile(os.path.join(update, n)) for n in NAMES):
        raise ValueError('%s: no update/data100.ofs + .bin (is Title Update 3 installed?)' % game)
    return update


def _originals(update):
    orig = os.path.join(update, 'original')
    if not os.path.isdir(orig):
        os.makedirs(orig)
        for n in NAMES:
            shutil.copy2(os.path.join(update, n), os.path.join(orig, n))
    return orig


def build(ofs, bin_, files):
    """New (ofs, bin) bytes: the archive's entries with `files` ({key: bytes}) replacing or added after them."""
    entries = parse_index(ofs)
    old = {k: bin_[PAYLOAD + start:PAYLOAD + start + size] for k, _, start, size in entries}
    order = [(k, w) for k, w, _, _ in entries] + [(k, 0) for k in files if k not in old]
    keys, offs, payload = [], [], bytearray()
    for k, w in order:
        data = files.get(k, old.get(k))
        offs.append(len(payload) | (len(data) & 0xF))
        keys.append(struct.pack('>II', k, w))
        payload += data + bytes(-len(data) % 16)
    offs.append(len(payload))
    b = boxes(ofs)
    head = ofs[b[b'head'][0] - 8:b[b'head'][0] + b[b'head'][1]]
    new_ofs = (ofs[:b[b'ftyp'][0] - 8 + 8 + b[b'ftyp'][1]] + head + _box(b'ofsi', b''.join(keys)) +
               _box(b'ofsd', struct.pack('>%dI' % len(offs), *offs)))
    if bin_[PAYLOAD - 4:PAYLOAD] != b'imge':
        raise ValueError('data100.bin: no imge box at 0x%X' % (PAYLOAD - 8))
    header = bytearray(bin_[:PAYLOAD])
    struct.pack_into('>I', header, PAYLOAD - 8, 8 + len(payload))
    return new_ofs, bytes(header) + bytes(payload)


def install(game, *srcs):
    update = _update_dir(game)
    orig = _originals(update)
    ofs, bin_ = (open(os.path.join(orig, n), 'rb').read() for n in NAMES)
    files = {}
    for src in srcs:
        names = sorted(os.path.relpath(os.path.join(r, f), src).replace(os.sep, '/')
                       for r, _, fs in os.walk(src) for f in fs)
        for name in names:                      # a file in a folder: under the key of its path (ric/alo/x.alo)
            path = os.path.join(src, name)
            if os.path.isfile(path):
                key = int(name[4:12], 16) if re.fullmatch(r'key_[0-9a-fA-F]{8}\.bin', name) else key_of(name)
                files[key] = open(path, 'rb').read()
                print('%08x %10d  %s' % (key, len(files[key]), name))
    new_ofs, new_bin = build(ofs, bin_, files)
    for n, data in zip(NAMES, (new_ofs, new_bin)):
        tmp = os.path.join(update, n + '.tmp')
        open(tmp, 'wb').write(data)
        os.replace(tmp, os.path.join(update, n))
    print('%s: %d entries, %d bytes' % (update, len(parse_index(new_ofs)), len(new_bin)))


def restore(game):
    update = _update_dir(game)
    orig = os.path.join(update, 'original')
    if not os.path.isdir(orig):
        print('nothing to restore: %s was never changed' % update)
        return
    for n in NAMES:
        shutil.copy2(os.path.join(orig, n), os.path.join(update, n))
    shutil.rmtree(orig)
    print('restored the title update\'s own %s' % ' + '.join(NAMES))


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    game, cmd = argv[0], argv[1]
    if cmd == 'install' and len(argv) >= 3:
        install(game, *argv[2:])
    elif cmd == 'restore':
        restore(game)
    elif cmd == 'list':
        update = _update_dir(game)
        changed = os.path.isdir(os.path.join(update, 'original'))
        for k, w, start, size in parse_index(open(os.path.join(update, NAMES[0]), 'rb').read()):
            print('%08x %d %10d %10d' % (k, w, start, size))
        print('(changed: originals in update/original)' if changed else '(the title update\'s own)')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (ValueError, KeyError, IOError) as e:
        sys.exit('overlay: %s' % (e.args[0] if e.args else e))
