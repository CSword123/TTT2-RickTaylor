"""LZX decoder for Xbox 360 XMemCompress streams (the 0x0FF512ED files of Splatterhouse 2010).

LZX as in the Microsoft spec: 16-bit little-endian words read most-significant bit first, verbatim / aligned /
uncompressed blocks, three repeated offsets, E8 call translation. XMemCompress splits the stream into frames: each
frame starts with a big-endian 16-bit compressed size (0xFF then 16-bit uncompressed + 16-bit compressed sizes for a
frame shorter than 32 KiB), and the bit reader restarts at each frame.
"""
import struct
import sys

MIN_MATCH = 2
NUM_CHARS = 256
PRETREE_NUM = 20
ALIGNED_NUM = 8
NUM_PRIMARY_LENGTHS = 7
NUM_SECONDARY_LENGTHS = 249
FRAME = 0x8000

POS_BASE = [0] * 52
EXTRA_BITS = [0] * 52
_j = 0
for _i in range(0, 52, 2):
    EXTRA_BITS[_i] = EXTRA_BITS[_i + 1] = _j
    if _i != 0 and _j < 17:
        _j += 1
_j = 0
for _i in range(52):
    POS_BASE[_i] = _j
    _j += 1 << EXTRA_BITS[_i]


class Bits:
    def __init__(self, data):
        self.d = data
        self.p = 0
        self.buf = 0
        self.n = 0

    def _fill(self):
        while self.n <= 16:
            if self.p + 1 < len(self.d):
                w = self.d[self.p] | (self.d[self.p + 1] << 8)
            else:
                w = 0
            self.p += 2
            self.buf |= w << (16 - self.n)
            self.n += 16

    def peek(self, k):
        self._fill()
        return (self.buf >> (32 - k)) & ((1 << k) - 1)

    def drop(self, k):
        self.buf = (self.buf << k) & 0xFFFFFFFF
        self.n -= k

    def read(self, k):
        if k == 0:
            return 0
        if k > 16:
            hi = self.read(k - 16)
            return (hi << 16) | self.read(16)
        v = self.peek(k)
        self.drop(k)
        return v

    def align(self):
        """Drop to the next 16-bit boundary (for uncompressed blocks)."""
        r = self.n % 16
        if r:
            self.drop(r)


class Huff:
    def __init__(self, lens):
        self.lens = list(lens)
        maxl = max(self.lens) if any(self.lens) else 0
        self.maxl = maxl
        self.empty = maxl == 0
        # lookup table over maxl bits: (symbol << 5) | length
        self.table = table = [0] * (1 << maxl) if maxl else []
        code = 0
        for L in range(1, maxl + 1):
            for sym, l in enumerate(self.lens):
                if l == L:
                    lo = code << (maxl - L)
                    v = (sym << 5) | L
                    for k in range(lo, lo + (1 << (maxl - L))):
                        table[k] = v
                    code += 1
            code <<= 1
        if maxl and code >> 1 > (1 << maxl):
            raise ValueError('over-subscribed huffman table')

    def decode(self, b):
        if b.n < 17:
            b._fill()
        v = self.table[(b.buf >> (32 - self.maxl)) & ((1 << self.maxl) - 1)]
        if v == 0:
            raise ValueError('bad huffman code')
        b.drop(v & 31)
        return v >> 5


def read_lengths(b, lens, first, last):
    pre = Huff([b.read(4) for _ in range(PRETREE_NUM)])
    x = first
    while x < last:
        z = pre.decode(b)
        if z == 17:
            for _ in range(b.read(4) + 4):
                lens[x] = 0
                x += 1
        elif z == 18:
            for _ in range(b.read(5) + 20):
                lens[x] = 0
                x += 1
        elif z == 19:
            n = b.read(1) + 4
            z = pre.decode(b)
            v = (lens[x] - z) % 17
            for _ in range(n):
                lens[x] = v
                x += 1
        else:
            lens[x] = (lens[x] - z) % 17
            x += 1


class LZX:
    def __init__(self, window_bits=17):
        self.wsize = 1 << window_bits
        slots = {15: 30, 16: 32, 17: 34, 18: 36, 19: 38, 20: 42, 21: 50}[window_bits]
        self.main_elems = NUM_CHARS + slots * 8
        self.main_lens = [0] * self.main_elems
        self.len_lens = [0] * NUM_SECONDARY_LENGTHS
        self.R = [1, 1, 1]
        self.out = bytearray()
        self.header_read = False
        self.e8 = 0
        self.block_remaining = 0
        self.block_type = 0

    def frame(self, data, out_len):
        """Decode one frame (bit reader restarted) producing out_len bytes."""
        b = Bits(data)
        start = len(self.out)
        out = self.out
        if not self.header_read:
            if b.read(1):
                self.e8 = b.read(32)
            self.header_read = True
        while len(out) - start < out_len:
            if self.block_remaining == 0:
                if b.p - b.n // 8 >= len(data) - 1:      # the frame's bytes are used up: the stream's last frame
                    break
                self.block_type = b.read(3)
                self.block_remaining = self.block_len = b.read(24)
                bt = self.block_type
                if bt == 2:
                    self.aligned = Huff([b.read(3) for _ in range(ALIGNED_NUM)])
                if bt in (1, 2):
                    read_lengths(b, self.main_lens, 0, 256)
                    read_lengths(b, self.main_lens, 256, self.main_elems)
                    self.main = Huff(self.main_lens)
                    read_lengths(b, self.len_lens, 0, NUM_SECONDARY_LENGTHS)
                    self.length = Huff(self.len_lens)
                elif bt == 3:
                    b.align()
                    # after the alignment the bit buffer may hold 16 bits already read
                    raw = b.p - (b.n // 8)
                    self.R = list(struct.unpack_from('<3I', data, raw))
                    b.p = raw + 12
                    b.buf = 0
                    b.n = 0
                    self.raw_pos = b.p
                else:
                    raise ValueError('bad block type %d at out %d' % (bt, len(out)))
            todo = min(self.block_remaining, out_len - (len(out) - start))
            if self.block_type == 3:
                out += data[b.p:b.p + todo]
                b.p += todo
                self.block_remaining -= todo
                if self.block_remaining == 0 and self.block_len & 1:
                    b.p += 1
                continue
            end = len(out) + todo
            while len(out) < end:
                s = self.main.decode(b)
                if s < NUM_CHARS:
                    out.append(s)
                    continue
                s -= NUM_CHARS
                ml = s & NUM_PRIMARY_LENGTHS
                if ml == NUM_PRIMARY_LENGTHS:
                    ml += self.length.decode(b)
                ml += MIN_MATCH
                slot = s >> 3
                if slot > 2:
                    eb = EXTRA_BITS[slot]
                    if self.block_type == 2 and eb >= 3:
                        off = POS_BASE[slot] - 2 + (b.read(eb - 3) << 3) + self.aligned.decode(b)
                    elif self.block_type == 2 and eb > 0:
                        off = POS_BASE[slot] - 2 + b.read(eb)
                    else:
                        off = POS_BASE[slot] - 2 + b.read(eb)
                    self.R = [off, self.R[0], self.R[1]]
                elif slot == 0:
                    off = self.R[0]
                elif slot == 1:
                    off = self.R[1]
                    self.R[1] = self.R[0]
                    self.R[0] = off
                else:
                    off = self.R[2]
                    self.R[2] = self.R[0]
                    self.R[0] = off
                src = len(out) - off
                if src < 0:
                    raise ValueError('match before start')
                for k in range(ml):
                    out.append(out[src + k])
            self.block_remaining -= todo
            # a match may run past the frame end
            over = len(out) - start - out_len
            if over > 0:
                self.block_remaining -= over
        return b


def e8_fix(frame, pos, size):
    if size == 0:
        return frame
    f = bytearray(frame)
    n = len(f)
    i = 0
    while i < n - 10:
        if f[i] == 0xE8:
            v = struct.unpack_from('<i', f, i + 1)[0]
            cur = pos + i
            if -cur <= v < size:
                nv = v - cur if v >= 0 else v + size
                struct.pack_into('<i', f, i + 1, nv)
            i += 5
        else:
            i += 1
    return bytes(f)


def xmem_block(payload, p, size, window_bits=17):
    """One block: XMemCompress frames (u16 BE compressed size + LZX bits, 32 KiB out each, one LZX state) from
    payload[p:] until size bytes are out. Returns (bytes, position after the block)."""
    d = LZX(window_bits)
    while len(d.out) < size:
        clen, = struct.unpack_from('>H', payload, p)
        p += 2
        if clen == 0:                   # padding between blocks (jennifer.nif): not a frame, the header bit is next
            continue
        d.frame(payload[p:p + clen], min(FRAME, size - len(d.out)))
        p += clen
    return bytes(d.out[:size]), p


def header(data):
    """(block sizes, offset of the first block). After magic, version and hash: a 32-bit word (block count << 6 |
    2), then each block's uncompressed size in 20 bits (most significant bit first), padded to 32 bits."""
    w, = struct.unpack_from('>I', data, 12)
    blocks = (w >> 6) & 0xFFFF
    nbytes = ((20 * blocks + 31) // 32) * 4
    bits = int.from_bytes(data[16:16 + nbytes], 'big')
    total = nbytes * 8
    sizes = [(bits >> (total - 20 * (k + 1))) & 0xFFFFF for k in range(blocks)]
    return sizes, 16 + nbytes


def read_file(data, window_bits=17):
    """A Splatterhouse data file's bytes, decompressed if it is a 0x0FF512ED file."""
    if len(data) < 16 or struct.unpack_from('>I', data, 0)[0] != 0x0FF512ED:
        return data
    sizes, p = header(data)
    out = []
    for size in sizes:
        chunk, p = xmem_block(data, p, size, window_bits)
        out.append(chunk)
    return b''.join(out)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    out = read_file(open(src, 'rb').read())
    open(dst, 'wb').write(out)
    print('%s: %d bytes' % (dst, len(out)))
