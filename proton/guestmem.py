"""Read, write and scan the guest (Xbox 360) memory of the recomp running under proton/run.sh, from Linux.

The game's 4 GB guest space is one ~4.02 GB reservation in the exe's process; /proc/<pid>/mem reaches it (the game is
a descendant of this shell, so ptrace_scope 1 allows it). Values are big-endian, as the guest sees them.

python3 proton/guestmem.py read <guest addr> [bytes]          hex dump
python3 proton/guestmem.py write32 <guest addr> <value>       one big-endian word
python3 proton/guestmem.py find <hex bytes> [lo hi]           where the bytes are
python3 proton/guestmem.py scan new <value> [lo hi]           [WIDTH=1|2|4] values == (default range: the heaps, 0x40000000-0xA0000000)
python3 proton/guestmem.py scan next <value>                  keep candidates that now hold value
python3 proton/guestmem.py scan list
"""
import json
import os
import struct
import sys

import numpy as np

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'guestmem_state.json')
SPAN = 0x100000000


def game_pid():
    for p in os.listdir('/proc'):
        if not p.isdigit():
            continue
        try:
            cmd = open('/proc/%s/cmdline' % p, 'rb').read()
        except OSError:
            continue
        exe = cmd.split(b'\0')[0]
        if not exe.lower().endswith(b'.exe') or b'cmd.exe' in exe.lower() or b'steam.exe' in exe.lower():
            continue
        if b'tekken_recomp' in exe or b'Tekken Tag Tournament 2.exe' in exe:
            return int(p)
    raise SystemExit('the game is not running')


def regions(pid):
    rows = []
    for line in open('/proc/%d/maps' % pid):
        a, b = (int(x, 16) for x in line.split()[0].split('-'))
        rows.append((a, b, line.split()[1]))
    return rows


def guest_base(pid):
    spans, cur = [], None
    for a, b, _ in regions(pid):
        if cur and a == cur[1]:
            cur[1] = b
        else:
            if cur:
                spans.append(cur)
            cur = [a, b]
    spans.append(cur)
    big = [s for s in spans if s[1] - s[0] >= SPAN]
    if len(big) != 1:
        raise SystemExit('cannot tell the guest reservation: %s' % big)
    return big[0][0]


def readable(pid, base, lo, hi):
    """(guest lo, guest hi) of the readable pieces of [lo, hi)."""
    out = []
    for a, b, perm in regions(pid):
        if 'r' not in perm:
            continue
        ga, gb = max(a - base, lo), min(b - base, hi)
        if ga < gb:
            out.append((ga, gb))
    return out


def main(argv):
    pid = game_pid()
    base = guest_base(pid)
    mem = open('/proc/%d/mem' % pid, 'r+b', buffering=0)
    cmd = argv[0]
    if cmd == 'read':
        addr, n = int(argv[1], 16), int(argv[2], 0) if len(argv) > 2 else 64
        mem.seek(base + addr)
        d = mem.read(n)
        for i in range(0, len(d), 16):
            print('%08X  %s' % (addr + i, ' '.join(d[i + j:i + j + 4].hex() for j in range(0, 16, 4))))
    elif cmd == 'write32':
        mem.seek(base + int(argv[1], 16))
        mem.write(struct.pack('>I', int(argv[2], 0) & 0xFFFFFFFF))
    elif cmd == 'find':                     # find <hex bytes> [lo hi]: every place the bytes are
        needle = bytes.fromhex(argv[1])
        lo, hi = (int(argv[2], 16), int(argv[3], 16)) if len(argv) > 3 else (0, SPAN)
        for ga, gb in readable(pid, base, lo, hi):
            for o in range(ga, gb, 1 << 22):
                try:
                    mem.seek(base + o)
                    d = mem.read(min((1 << 22) + len(needle), gb - o))
                except OSError:
                    continue
                i = d.find(needle)
                while 0 <= i < (1 << 22):
                    print('%08X' % (o + i))
                    i = d.find(needle, i + 1)
    elif cmd == 'scan':
        sub = argv[1]
        width = int(os.environ.get('WIDTH', '4'))           # WIDTH=1/2/4: the value's size in bytes
        dt = {1: 'u1', 2: '>u2', 4: '>u4'}[width]
        if sub == 'new':
            value = int(argv[2], 0)
            lo, hi = (int(argv[3], 16), int(argv[4], 16)) if len(argv) > 4 else (0x40000000, 0xA0000000)
            found = []
            for ga, gb in readable(pid, base, lo, hi):
                for o in range(ga, gb, 1 << 22):
                    n = min(1 << 22, gb - o)
                    try:
                        mem.seek(base + o)
                        d = mem.read(n)
                    except OSError:
                        continue
                    w = np.frombuffer(d[:len(d) // width * width], dt)
                    found.extend((o + width * np.nonzero(w == value)[0]).tolist())
            json.dump(found, open(STATE, 'w'))
            print('%d candidates' % len(found))
        elif sub == 'next':
            value = int(argv[2], 0)
            keep = []
            for g in json.load(open(STATE)):
                mem.seek(base + g)
                if int.from_bytes(mem.read(width), 'big') == value:
                    keep.append(g)
            json.dump(keep, open(STATE, 'w'))
            print('%d candidates' % len(keep), ' '.join('%08X' % g for g in keep[:20]))
        elif sub == 'list':
            for g in json.load(open(STATE))[:200]:
                mem.seek(base + g)
                print('%08X %d' % (g, int.from_bytes(mem.read(width), 'big')))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
