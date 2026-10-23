"""Xbox 360 textures as Splatterhouse's NIFs store them (NiPersistentSrcTextureRendererData, tiling 1): the top mip of
a tiled DXT1 (format 4) or DXT5 (format 6) surface -> RGBA. The blocks keep PC byte order (no 16-bit swap, unlike
most Xbox 360 textures).

Tiling: the XGAddress2DTiledX/Y formulas (the surface is laid out in 4x4-block units, its width aligned to 32
blocks), applied to DXT blocks as the texels.
"""
import numpy as np

FORMATS = {4: ('dxt1', 8), 6: ('dxt5', 16)}


def _log_bpp(pitch):
    return (pitch >> 2) + ((pitch >> 1) >> (pitch >> 2))


def tiled_xy(offset, width, pitch):
    """Texel (x, y) of linear tiled offsets (numpy arrays) on a surface `width` texels wide, `pitch` bytes each."""
    aw = (width + 31) & ~31
    lb = _log_bpp(pitch)
    ob = offset << lb
    ot = ((ob & ~4095) >> 3) + ((ob & 1792) >> 2) + (ob & 63)
    om = ot >> (7 + lb)
    macro_x = (om % (aw >> 5)) << 2
    tile = (((ot >> (5 + lb)) & 2) + (ob >> 6)) & 3
    x = ((macro_x + tile) << 3) + (((((ot >> 1) & ~15) + (ot & 15)) & ((pitch << 3) - 1)) >> lb)
    macro_y = (om // (aw >> 5)) << 2
    tile = ((ot >> (6 + lb)) & 1) + ((ob & 2048) >> 10)
    y = (((macro_y + tile) << 3) + ((((ot & (((pitch << 6) - 1) & ~31)) + ((ot & 15) << 1)) >> (3 + lb)) & ~1)
         + ((ot & 16) >> 4))
    return x, y


def untile(data, wblocks, hblocks, pitch):
    """Linear blocks (hblocks, wblocks, pitch) bytes from a tiled surface."""
    aw = (wblocks + 31) & ~31
    ah = (hblocks + 31) & ~31
    n = aw * ah
    raw = np.frombuffer(data, np.uint8)
    if len(raw) < n * pitch:
        raw = np.concatenate([raw, np.zeros(n * pitch - len(raw), np.uint8)])
    raw = raw[:n * pitch].reshape(n, pitch)
    x, y = tiled_xy(np.arange(n), aw, pitch)
    out = np.zeros((ah, aw, pitch), np.uint8)
    out[y, x] = raw
    return out[:hblocks, :wblocks]


def _565(c):
    r = ((c >> 11) & 31) * 255 // 31
    g = ((c >> 5) & 63) * 255 // 63
    b = (c & 31) * 255 // 31
    return np.stack([r, g, b], -1).astype(np.int32)


def dxt1_colour(blk, alpha_allowed=True):
    """(..., 8) little-endian DXT1 colour blocks -> (..., 4, 4, 4) RGBA."""
    c0 = blk[..., 0].astype(np.int32) | (blk[..., 1].astype(np.int32) << 8)
    c1 = blk[..., 2].astype(np.int32) | (blk[..., 3].astype(np.int32) << 8)
    bits = (blk[..., 4].astype(np.uint32) | (blk[..., 5].astype(np.uint32) << 8) |
            (blk[..., 6].astype(np.uint32) << 16) | (blk[..., 7].astype(np.uint32) << 24))
    a, b = _565(c0), _565(c1)
    four = (c0 > c1) | (not alpha_allowed)
    p2 = np.where(four[..., None], (2 * a + b) // 3, (a + b) // 2)
    p3 = np.where(four[..., None], (a + 2 * b) // 3, 0)
    pal = np.stack([a, b, p2, p3], -2)                                   # (..., 4 colours, 3)
    alpha = np.full(pal.shape[:-1], 255, np.int32)
    alpha[..., 3] = np.where(four, 255, 0)
    pal = np.concatenate([pal, alpha[..., None]], -1)                    # (..., 4, 4)
    idx = (bits[..., None] >> (2 * np.arange(16, dtype=np.uint32))) & 3  # (..., 16)
    px = np.take_along_axis(pal, idx[..., None].astype(np.int64), -2)    # (..., 16, 4)
    return px.reshape(blk.shape[:-1] + (4, 4, 4))


def dxt5_alpha(blk):
    """(..., 8) DXT5 alpha blocks -> (..., 4, 4)."""
    a0 = blk[..., 0].astype(np.int32)
    a1 = blk[..., 1].astype(np.int32)
    bits = np.zeros(blk.shape[:-1], np.uint64)
    for k in range(6):
        bits |= blk[..., 2 + k].astype(np.uint64) << np.uint64(8 * k)
    eight = a0 > a1
    pal = [a0, a1]
    for k in range(1, 7):
        pal.append(np.where(eight, ((7 - k) * a0 + k * a1) // 7,
                            ((5 - k) * a0 + k * a1) // 5 if k < 5 else (0 if k == 5 else 255)))
    pal = np.stack(pal, -1)
    idx = ((bits[..., None] >> (np.uint64(3) * np.arange(16, dtype=np.uint64))) & np.uint64(7)).astype(np.int64)
    return np.take_along_axis(pal, idx, -1).reshape(blk.shape[:-1] + (4, 4))


def decode(tex):
    """A NiPersistentSrcTextureRendererData block (nifblocks.read) -> (h, w, 4) uint8 RGBA of its top mip."""
    kind, pitch = FORMATS[tex['pixel_format']]
    w, h, _ = tex['mips'][0]
    wb, hb = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
    data = tex['pixels']
    if tex['tiling']:
        blocks = untile(data, wb, hb, pitch)
    else:
        blocks = np.frombuffer(data, np.uint8)[:wb * hb * pitch].reshape(hb, wb, pitch)
    if kind == 'dxt1':
        px = dxt1_colour(blocks)
    else:
        px = dxt1_colour(blocks[..., 8:], alpha_allowed=False)
        px[..., 3] = dxt5_alpha(blocks[..., :8])
    img = px.transpose(0, 2, 1, 3, 4).reshape(hb * 4, wb * 4, 4)
    return np.clip(img[:h, :w], 0, 255).astype(np.uint8)
