"""Blood off Rick's clothes: Splatterhouse paints its spatter into the colour maps (every Rick model shares these,
Mirror Rick's too), so the jeans (with the waistband's underwear) and the shoes are cleaned here.

python -m ttt2rick.convert.clean <texture folder> <out folder>     before / after previews of CLEAN

Blood is the only saturated red in them (denim is blue-grey, the shoes black, white and yellow-green, the dirt
brown): blood_weight finds it, softly at its pinkish edges, and fill paints it over with the colours around it
(a push-pull pyramid: the known pixels averaged at coarser and coarser scales, the holes taken from the first
scale that has them, from clean pixels only), blended in by the weight. The shoes' stains are wide and cross their
white, black and yellow-green, the white mostly stained, so copying clean pixels leaves blotches there. Blood
takes green and blue away and leaves red about as bright as what it lies on, so a shoe stain keeps its own red as
its brightness and gets the colour of the material most clean pixels around it are (within MAJORITY_RADIUS, each
material filled on its own); on black the brightness is capped near the black's (thick blood is redder than it).

clean_skin takes the bright red spatter off Mirror Rick's own body texture (SKIN: his blue-teal marble skin): red
over green and blue, bright enough, painted over by fill with the marble's colours around at the pixel's own
brightness (so the marble's grain stays). His thin dark veins and the pinkish wash are his, and stay.

clean_picture does the same for the picture of him (work/art/rick_taylor.png) that ttt2rick.convert.portrait makes
his select portraits from: the blood there lies on his skin as well (the right arm all over, see-through smears on
the chest) and on the shorts.
"""
import os
import sys

import numpy as np
from PIL import Image

# texture -> redness (1 - max(g, b) / r) from which a pixel starts to be blood, and where it fully is. Fresh blood
# is 0.45 and more, dried drops on the denim (about 117, 72, 62) 0.3-0.45; the waistband's tan is under 0.25. On the
# shoes the white parts' brownish smears (0.2-0.3) go too, the yellow-green and black never count (g > r, too dark).
# Dried drops on the denim are as dark as (24, 4, 8): the darkness cut-off is low (the denim's own darks are bluish).
# Diluted blood on white is a pink tint: red over green and blue, which are about equal (the waistband's tan has
# green well over blue).
CLEAN = {'rick_lowerbody_base.png': (0.25, 0.38, False), 'rick_globeshoes_base.png': (0.10, 0.22, True)}
SKIN = {'mirror_rick_body_base.png': (0.12, 0.30)}    # texture -> redness ramp (clean_skin); red from 60 to 100
PRINT_RADIUS = 3                        # pixels around which print makes a pixel part of the print area
MAJORITY_RADIUS = 6                     # pixels (shoes, 256 x 256)
LIGHT_CLOTH = 140                       # mean brightness from which a clean pixel of the jeans' map is light cloth
DARK_NEARER = 4                         # how much nearer dark cloth must be for a bright jeans stain to be on it
BRIGHT_BLOOD = 90                       # a stain's red from which it is bright (fresh: the cream band's)
LIGHT_STAIN = 120                       # a shoe stain's red from which it lies on white, whatever is around
DARK_STAIN = 60                         # and under which, with no clean pixel around, on black


def blood_weight(rgb, ramp=(0.25, 0.38)):
    """0..1 per pixel: how much it is blood (red over green and blue by ramp, not too dark), grown a pixel."""
    r, g, b = (rgb[..., i].astype(np.float32) for i in range(3))
    redness = 1 - np.maximum(g, b) / np.maximum(r, 1.0)
    w = np.clip((redness - ramp[0]) / (ramp[1] - ramp[0]), 0, 1) * np.clip((r - 12.0) / 12.0, 0, 1)
    w *= np.clip((45.0 - (g - b)) / 20.0, 0, 1)     # blood's green and blue are alike; orange print has g >> b
    # dried drops on dark cloth: (8, 0, 0), (24, 16, 16), (54, 38, 35), (65, 48, 57); the denim is bluish (21, 24, 29:
    # blue about 8 over red), the black neutral, so a dark pixel with red over blue (and not under green) is blood
    dark = np.clip((r - b - 1.0) / 5.0, 0, 1) * (r >= g - 2) * np.clip((90.0 - (r + g + b) / 3) / 20.0, 0, 1)
    dark *= np.clip((22.0 - (g - b)) / 10.0, 0, 1)   # not the orange print's dark edges (g >> b)
    w = np.maximum(w, dark)
    pink = np.clip((r - np.maximum(g, b) - 6.0) / 8.0, 0, 1) * np.clip((12.0 - np.abs(g - b)) / 6.0, 0, 1)
    w = np.maximum(w, pink * np.clip((r - 120.0) / 40.0, 0, 1))
    grown = w.copy()                          # the spatter's dark rims: one pixel around it
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        grown = np.maximum(grown, 0.6 * np.roll(w, (dy, dx), (0, 1)))
    return grown


def fill(img, known):
    """img (h, w, c) float with the pixels where known is False painted over from their surroundings, and how near
    the known pixels are (1 on them, halving with each scale further out)."""
    known = known.astype(np.float32)
    levels = [(img * known[..., None], known)]
    while min(levels[-1][1].shape) > 1:
        v, k = levels[-1]
        h, w = (k.shape[0] + 1) // 2 * 2, (k.shape[1] + 1) // 2 * 2
        v = np.pad(v, ((0, h - v.shape[0]), (0, w - v.shape[1]), (0, 0)))
        k = np.pad(k, ((0, h - k.shape[0]), (0, w - k.shape[1])))
        levels.append((v.reshape(h // 2, 2, w // 2, 2, -1).sum((1, 3)), k.reshape(h // 2, 2, w // 2, 2).sum((1, 3))))
    def upsample(x, shape):
        return np.asarray(Image.fromarray(x.astype(np.float32), 'F').resize((shape[1], shape[0]), Image.BILINEAR))
    v, k = levels[-1]
    out = v / np.maximum(k, 1e-6)[..., None]
    near = np.clip(k, 0, 1)
    for v, k in reversed(levels[:-1]):
        near = np.clip(k, 0, 1) + (1 - np.clip(k, 0, 1)) * 0.5 * upsample(near, k.shape)
        up = np.stack([upsample(out[..., c], k.shape) for c in range(out.shape[-1])], -1)
        mine = v / np.maximum(k, 1e-6)[..., None]
        a = np.clip(k, 0, 1)[..., None]        # a level's own average where it has known pixels
        out = mine * a + up * (1 - a)
    return out, near


def materials(rgb):
    """A clean pixel's material: 0 dark, 1 light, 2 the yellow-green print; -1 the texture's empty black around its
    pieces. (White, black and blood all have green about equal to blue.)"""
    r, g, b = (rgb[..., i] for i in range(3))
    mean = rgb.mean(-1)
    kind = np.where(mean < 6, -1, np.where(mean < 70, 0, 1))
    return np.where((g > b + 45) & (mean >= 50), 2, kind)    # the print, ochre where dirty: green far over blue


def box(x, r):
    """x (h, w) summed over the (2r + 1)^2 window around each pixel (zero outside)."""
    c = np.pad(x, ((r + 1, r), (r + 1, r))).cumsum(0).cumsum(1)
    return c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:] - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1]


def clean(rgba, ramp=(0.25, 0.38, False)):
    """The colour map (h, w, 4 uint8) without its blood."""
    a = np.asarray(rgba)
    w = blood_weight(a, ramp[:2])
    if not (w > 0.2).any():
        return a.copy()
    rgb = a[..., :3].astype(np.float32)
    clean_px = w < 0.05                         # the colours around come from clean pixels only
    if ramp[2]:
        kind = materials(rgb)
        masks = [clean_px & (kind == k) for k in range(3)]
        fills = [fill(rgb, m) for m in masks]
        counts = np.stack([box(m.astype(np.float64), MAJORITY_RADIUS) for m in masks])
        share = counts / np.maximum(counts.sum(0), 1e-6)
        # the material most clean pixels around are; white already at 30% while black is no majority (the stains lie
        # mostly on white); with none around (the white strips are mostly stained), by its own brightness, and the
        # nearest (white unless black is clearly nearer) between; a bright stain lies on white unless black is most
        # around (thick blood on black is bright)
        near = np.stack([n for _, n in fills])
        some = counts.sum(0) > 0
        r, g = rgb[..., 0], rgb[..., 1]
        alone = np.where(r < DARK_STAIN, 0, np.where(r >= LIGHT_STAIN, 1, np.argmax(near * [[[0.7]], [[1.0]], [[1.0]]], 0)))
        under = np.where(some, np.argmax(counts, 0), alone)
        under = np.where(some & (share[1] >= 0.3) & (share[0] < 0.5), 1, under)
        under = np.where((under == 0) & (r >= LIGHT_STAIN) & ~(some & (share[0] >= 0.6)), 1, under)
        # brown on the yellow-green print (its green over its red): blood too
        w = np.maximum(w, (under == 2) * np.clip((r - g * 1.02) / 15.0, 0, 1) * np.clip((r - 60.0) / 20.0, 0, 1))
        colour = np.choose(under[..., None], [f for f, _ in fills])
        grey = colour.mean(-1, keepdims=True)
        colour = np.where((under == 1)[..., None], grey + 0.3 * (colour - grey), colour)   # white is white
        lum = np.where(under == 0, np.minimum(r, 1.4 * colour.mean(-1) + 8),
                       np.where(under == 1, np.maximum(r, 0.8 * colour[..., 0]), r))      # no dark specks on white
        filled = colour * (lum / np.maximum(colour[..., 0], 1.0))[..., None]
    else:
        # light cloth (the underwear's cream waistband) and dark (denim, the belt loops) each filled from its own:
        # filled from everything around, the band's stains took the black belt strip's colour beside it (the user
        # saw it, 2026-10-27). A bright stain is light cloth unless dark cloth is clearly nearer, a dark one the nearer
        # cloth (fill's nearness: the band's left half is all blood, so a majority of the pixels around went to the
        # belt strip beside it)
        light = rgb.mean(-1) >= LIGHT_CLOTH
        fills = [fill(rgb, m) for m in (clean_px & ~light, clean_px & light)]
        bias = np.where(rgb[..., 0] >= BRIGHT_BLOOD, DARK_NEARER, 1.0)   # (dark, dried drops: on the denim)
        under = (fills[1][1] * bias >= fills[0][1]).astype(int)
        fills = [f for f, _ in fills]
        filled = np.choose(under[..., None], fills)
    out = a.copy()
    out[..., :3] = np.clip(rgb * (1 - w[..., None]) + filled * w[..., None] + 0.5, 0, 255).astype(np.uint8)
    if ramp[2]:
        out[..., :3] = print_dirt(out[..., :3])
    return out


def skin_weight(rgb, ramp=(0.12, 0.30)):
    """0..1 per pixel of Mirror Rick's skin: how much it is bright red blood, grown a pixel."""
    r, g, b = (rgb[..., i].astype(np.float32) for i in range(3))
    redness = 1 - np.maximum(g, b) / np.maximum(r, 1.0)
    w = np.clip((redness - ramp[0]) / (ramp[1] - ramp[0]), 0, 1) * np.clip((r - 60.0) / 40.0, 0, 1)
    grown = w.copy()
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        grown = np.maximum(grown, 0.6 * np.roll(w, (dy, dx), (0, 1)))
    return grown


def clean_skin(rgba, ramp=(0.12, 0.30)):
    """Mirror Rick's skin (h, w, 4 uint8) without its bright red blood: the colours around at the pixel's own
    brightness (0.6 to 1.3 of theirs)."""
    a = np.asarray(rgba)
    rgb = a[..., :3].astype(np.float32)
    w = skin_weight(a, ramp)[..., None]
    filled = fill(rgb, w[..., 0] < 0.05)[0]
    luma = np.array([0.3, 0.59, 0.11], np.float32)
    k = np.clip((rgb @ luma) / np.maximum(filled @ luma, 1.0), 0.6, 1.3)[..., None]
    out = a.copy()
    out[..., :3] = np.clip(rgb * (1 - w) + filled * k * w + 0.5, 0, 255).astype(np.uint8)
    return out


def print_dirt(rgb):
    """The shoes' yellow-green print without its dirt: the print is green over red (its darker printed patches
    too), mud and dried blood on it orange to brown (red as high as green or higher). Those pixels take the colour of
    the clean print around them at their own brightness, so the pattern's light and dark stays."""
    rgb = rgb.astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    on_print = (np.maximum(r, g) > b + 40) & (rgb.mean(-1) >= 30)
    near = box(on_print.astype(np.float64), PRINT_RADIUS) > 0.4 * (2 * PRINT_RADIUS + 1) ** 2
    clean_print = on_print & (g > r * 1.08)
    w = (on_print | near) * np.clip((r - g * 0.98) / 18.0, 0, 1) * np.clip((r - b - 25.0) / 20.0, 0, 1)
    if not (w > 0.2).any():
        return rgb.astype(np.uint8)
    colour = fill(rgb, clean_print & (w < 0.05))[0]
    lum = rgb.mean(-1, keepdims=True) / np.maximum(colour.mean(-1, keepdims=True), 1.0)
    fixed = colour * np.clip(lum, 0.25, 1.3)
    return np.clip(rgb * (1 - w[..., None]) + fixed * w[..., None] + 0.5, 0, 255).astype(np.uint8)


# The picture: redness from which a pixel starts to be blood on his skin, and where it fully is (clean skin is about
# 0.27, in shadow up to 0.33; the see-through smears 0.4 and more, fresh blood 0.7). The shorts' box (in its pixels):
# there the colours around come from the denim (blue at least as high as red) unless the holes' skin is clearly most
# around, and dark pixels with red over blue are dried blood. A stain keeps its red, lifted a little (blood darkens
# what it lies on), as its brightness against the colour around; on the denim no brighter than it.
PICTURE_RAMP = (0.33, 0.48)
SHORTS = (130, 765, 740, 1250)
LIFT = 1.12


def picture_weight(rgba):
    """0..1 per pixel of the picture: how much it is blood, grown two pixels (the smears' edges)."""
    rgb = rgba[..., :3].astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    red = 1 - np.maximum(g, b) / np.maximum(r, 1.0)
    w = np.clip((red - PICTURE_RAMP[0]) / (PICTURE_RAMP[1] - PICTURE_RAMP[0]), 0, 1) * np.clip((r - 14.0) / 12.0, 0, 1)
    dark = np.clip((red - 0.35) / 0.1, 0, 1) * np.clip((r - b - 2.0) / 6.0, 0, 1) * (r >= g - 2) \
        * np.clip((90.0 - (r + g + b) / 3) / 20.0, 0, 1)
    w = np.where(shorts_mask(r.shape), np.maximum(w, dark), w) * (rgba[..., 3] > 0)
    grown = w.copy()
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (0, 2), (0, -2), (2, 0), (-2, 0)):
        grown = np.maximum(grown, (0.8 if abs(dy + dx) == 1 else 0.5) * np.roll(w, (dy, dx), (0, 1)))
    return grown


def shorts_mask(shape):
    x0, y0, x1, y1 = SHORTS
    m = np.zeros(shape, bool)
    m[y0:y1, x0:x1] = True
    return m


def clean_picture(picture):
    """The picture (PIL RGBA) without its blood."""
    a = np.asarray(picture.convert('RGBA'))
    rgb = a[..., :3].astype(np.float32)
    w = picture_weight(a)
    shorts = shorts_mask(w.shape)
    known = (w < 0.05) & (a[..., 3] == 255) & (rgb.mean(-1) > 10)
    warm = (rgb[..., 0] > rgb[..., 2] + 12) & ~(shorts & (rgb.mean(-1) < 80))     # on the shorts only the holes' skin
    masks = [known & warm, known & (rgb[..., 2] >= rgb[..., 0] - 3)]                # skin, denim
    fills = [fill(rgb, m) for m in masks]
    counts = np.stack([box(m.astype(np.float64), MAJORITY_RADIUS * 2) for m in masks])
    under = np.where(shorts & ~(counts[0] > 2 * counts[1]), 1, 0)
    colour = np.choose(under[..., None], [f for f, _ in fills])
    # far from clean skin (the bloodied arm) its fill is an average of everything: there the skin's own tint (the
    # clean skin's median) at the fill's red
    skin = np.median(rgb[masks[0] & (rgb[..., 0] > 60)], 0)
    far = ((1 - np.clip(fills[0][1] * 4, 0, 1)) * (under == 0))[..., None]
    colour = colour * (1 - far) + skin / skin[0] * colour[..., :1] * far
    k = np.clip(LIFT * rgb[..., 0] / np.maximum(colour[..., 0], 1.0), 0.25, np.where(under == 0, 1.5, 1.0))
    out = a.copy()
    out[..., :3] = np.clip(rgb * (1 - w[..., None]) + colour * k[..., None] * w[..., None] + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(out)


def main():
    src, out = sys.argv[1:3]
    os.makedirs(out, exist_ok=True)
    for name, ramp in list(CLEAN.items()) + list(SKIN.items()):
        if not os.path.exists(os.path.join(src, name)):
            continue
        im = np.asarray(Image.open(os.path.join(src, name)).convert('RGBA'))
        after = clean_skin(im, ramp) if name in SKIN else clean(im, ramp)
        h, w = im.shape[:2]
        sheet = Image.new('RGB', (2 * w, h))
        sheet.paste(Image.fromarray(im).convert('RGB'), (0, 0))
        sheet.paste(Image.fromarray(after).convert('RGB'), (w, 0))
        sheet.save(os.path.join(out, name.replace('.png', '_before_after.png')))
        weight = skin_weight(im, ramp) if name in SKIN else blood_weight(im, ramp[:2])
        print('%s: %.1f%% of pixels were blood' % (name, 100 * (weight > 0.5).mean()))


if __name__ == '__main__':
    main()
