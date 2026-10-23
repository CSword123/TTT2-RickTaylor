"""Drive the recomp running under proton/run.sh (started with TTT2_FBDUMP=1) and look at it.

python3 proton/drive.py [--frames N] [--out shot.png] [--expect ref.png [--box x0,y0,x1,y1]] ["BUTTONS hold_ms [gap_ms]" ...]

Writes the presses to the game's pad_inject.txt (C:\\ttt2\\port\\ in the prefix; BUTTONS: START BACK UP DOWN LEFT RIGHT
A B X Y LB RB LS RS joined by '+', P2 for player 2), then waits until the game has written N more fbdump.bmp frames
(one each 60 presents, about a second) and saves the last as a PNG.
"""
import argparse
import os
import time

from PIL import Image

PORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pfx', 'pfx', 'drive_c', 'ttt2', 'port')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('presses', nargs='*')
    ap.add_argument('--frames', type=int, default=2)
    ap.add_argument('--out', default=os.path.join(PORT, 'shot.png'))
    ap.add_argument('--timeout', type=float, default=120)
    ap.add_argument('--expect', help='reference screenshot: exit 3 unless the screen matches it (in --box)')
    ap.add_argument('--box', default='0,0,1280,720', help='x0,y0,x1,y1 compared with --expect')
    ap.add_argument('--tolerance', type=float, default=12.0, help='mean grey difference allowed (0-255)')
    a = ap.parse_args()
    os.makedirs(PORT, exist_ok=True)
    fb = os.path.join(PORT, 'fbdump.bmp')
    if a.presses:
        tmp = os.path.join(PORT, 'pad_inject.tmp')
        with open(tmp, 'w') as f:
            f.write('\n'.join(a.presses) + '\n')
        os.replace(tmp, os.path.join(PORT, 'pad_inject.txt'))
    seen, last, end = 0, os.path.getmtime(fb) if os.path.exists(fb) else 0, time.time() + a.timeout
    while seen < a.frames:
        if time.time() > end:
            raise SystemExit('no new frame in %.0f s: is the game running with TTT2_FBDUMP=1?' % a.timeout)
        time.sleep(0.2)
        m = os.path.getmtime(fb) if os.path.exists(fb) else 0
        if m != last:
            seen, last = seen + 1, m
    time.sleep(0.3)                     # let the write finish
    shot = Image.open(fb).convert('RGB')
    shot.save(a.out)
    print(a.out)
    if a.expect:
        box = tuple(int(v) for v in a.box.split(','))
        def grey(im):
            im = im.crop(box).convert('L')
            return im.resize((max(1, im.width // 8), max(1, im.height // 8)))
        x, y = grey(shot), grey(Image.open(a.expect).convert('RGB'))
        diff = sum(abs(p - q) for p, q in zip(x.tobytes(), y.tobytes())) / (x.width * x.height)
        print('difference %.1f' % diff)
        if diff > a.tolerance:
            raise SystemExit(3)


if __name__ == '__main__':
    main()
