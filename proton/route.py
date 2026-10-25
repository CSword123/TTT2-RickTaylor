"""Drive the game (started here under Proton) to a Practice fight, checking each screen before the next press.

python3 proton/route.py [--exe tekken_recomp_linux.exe] [--rick] [--stop menu|select] [--stage-right 4] [--out fight.png]

--rick: TTT2_RICK=1, and the player picks Rick's cell (top row, column 19); otherwise Marduk. The practice dummy is
Marduk. Presses sent while a screen animates are often dropped, so every step looks at the screen (a menu's red
highlighted icon, a known screen) and presses again until it moves on.
"""
import argparse
import os
import subprocess
import sys
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = os.path.join(HERE, 'pfx', 'pfx', 'drive_c', 'ttt2', 'port')
INSTALL = os.path.join(HERE, 'install', 'Tekken Tag Tournament 2')
REF = os.path.join(HERE, 'ref')


def drive(*presses, frames=1, out=None):
    cmd = [sys.executable, os.path.join(HERE, 'drive.py'), '--frames', str(frames), *presses]
    if out:
        cmd += ['--out', out]
    subprocess.run(cmd, check=True, capture_output=True)
    return Image.open(out or os.path.join(PORT, 'shot.png')).convert('RGB')


def grey_diff(a, b, box):
    def grey(im):
        im = im.crop(box).convert('L')
        return im.resize((max(1, im.width // 8), max(1, im.height // 8))).tobytes()
    x, y = grey(a), grey(b)
    return sum(abs(p - q) for p, q in zip(x, y)) / len(x)


def like(shot, ref, box, tolerance=12):
    return grey_diff(shot, Image.open(os.path.join(REF, ref)).convert('RGB'), box) <= tolerance


def tag_lit(shot):
    """The Tag/Solo prompt's Tag box has its green frame (left edge)."""
    r, g, b = shot.getpixel((230, 185))
    return g - r > 40 and g - b > 60


def red(shot, x, y):
    r, g, b = shot.getpixel((x, y))
    return r > 140 and r - g > 70 and r - b > 70


def green(shot, x, y):
    r, g, b = shot.getpixel((x, y))
    return g > 200 and g - r > 100 and g - b > 100


MENU_BOX = (100, 100, 760, 470)          # the menu's text column
LABEL_BOX = (520, 290, 770, 320)         # the select screen's mode label (PRACTICE)
GRID_BOX = (90, 400, 1190, 610)          # the select grid (the same in every mode)


ROWS = [70, 122, 173, 224, 275, 326, 377, 428, 479]   # the menus' icons (left edge x 106), the highlighted one red


def highlighted(shot):
    hits = [i for i, y in enumerate(ROWS) if red(shot, 106, y)]
    return hits[0] if len(hits) == 1 else None


def choose_row(target, what, tries=20):
    for _ in range(tries):
        shot = drive(frames=2)
        row = highlighted(shot)
        if row == target:
            return
        drive('DOWN 120 350' if row is None or row < target else 'UP 120 350', frames=1)
    raise SystemExit('route: could not highlight %s' % what)


def until(test, press, tries=12, what=''):
    for _ in range(tries):
        shot = drive(frames=1)
        if test(shot):
            return shot
        drive(press, frames=1)
    raise SystemExit('route: stuck before %s (see %s)' % (what, os.path.join(PORT, 'shot.png')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', default='tekken_recomp_linux.exe')
    ap.add_argument('--rick', action='store_true')
    ap.add_argument('--stop', choices=['menu', 'select'])
    ap.add_argument('--arcade', action='store_true', help='Arcade Battle instead of Practice (no dummy; frames '
                    'from the pick on are saved as <out>_NN.png)')
    ap.add_argument('--tag', action='store_true', help='with --arcade: a tag team, the player\'s fighter and Marduk '
                    '(the VS screen shows both)')
    ap.add_argument('--partner-left', type=int, default=3, help='with --rick --tag: the partner is this many cells '
                    'left of the cell below Rick\'s (3: Marduk)')
    ap.add_argument('--dummy-rick', action='store_true', help='Practice: the player is Marduk and the dummy Rick '
                    '(TTT2_RICK=1)')
    ap.add_argument('--stage-right', type=int, default=4)       # Germany, Historic Town Square
    ap.add_argument('--out', default=os.path.join(PORT, 'fight.png'))
    a = ap.parse_args()

    env = dict(os.environ, TTT2_FBDUMP='1')
    if a.rick or a.dummy_rick:
        env['TTT2_RICK'] = '1'
    fb = os.path.join(PORT, 'fbdump.bmp')
    if os.path.exists(fb):
        os.remove(fb)
    winexe = subprocess.run([os.path.join(HERE, 'winpath'), os.path.join(INSTALL, a.exe)], capture_output=True,
                            text=True).stdout.strip()
    args = ['cmd', '/c', '%s 2> dev.log' % a.exe] if a.exe.startswith('tekken_recomp') else [winexe]
    subprocess.Popen([os.path.join(HERE, 'run.sh'), *args], cwd=INSTALL, env=env,
                     stdout=open(os.path.join(HERE, 'game.out'), 'w'), stderr=subprocess.STDOUT)
    drive(frames=3)

    # intro, title, profile and notices: START on the movies and the title, A on the dialogs, until the main menu
    for i in range(30):
        shot = drive(frames=1)
        if like(shot, 'menu.png', MENU_BOX):
            break
        drive('START 150 300' if i % 2 == 0 else 'A 150 300', frames=2)
    else:
        raise SystemExit('route: no main menu')
    if a.stop == 'menu':
        drive(frames=1, out=a.out)
        return
    choose_row(1, 'Offline Mode')
    until(lambda s: like(s, 'offline.png', (160, 100, 760, 470)), 'A 150 300', what='the Offline menu')
    choose_row(0 if a.arcade else 6, 'Arcade Battle' if a.arcade else 'Practice')
    until(lambda s: not like(s, 'offline_practice.png', (160, 100, 760, 470)), 'A 150 300', what='the mode')
    if a.tag:
        until(tag_lit, 'LEFT 120 200', what='Tag highlighted')
    else:
        until(lambda s: green(s, 380, 252), 'RIGHT 120 200', what='Solo highlighted')
    drive('A 150 300', frames=1)            # Tag or Solo; then wait (a second A would pick a fighter)
    for _ in range(20):
        shot = drive(frames=1)
        if like(shot, 'select_practice.png', GRID_BOX, 25) and not green(shot, 380, 252) and \
                (a.arcade or like(shot, 'select_practice.png', LABEL_BOX)):
            break
        if tag_lit(shot) if a.tag else green(shot, 380, 252):
            drive('A 150 300', frames=1)
    else:
        raise SystemExit('route: no character select')
    # the cursor starts on Jun (middle row, column 10): Marduk is column 16
    for _ in range(6):
        drive('RIGHT 100 200', frames=1)
    if a.rick:
        for _ in range(3):
            drive('RIGHT 100 200', frames=1)
        drive('UP 100 200', frames=1)
    if a.stop == 'select':
        drive(frames=1, out=a.out)
        return
    if a.arcade:
        drive('A 150 300', frames=1)
        if a.tag:                            # the partner: Marduk (the cursor stays on the first pick)
            drive(frames=8)
            if a.rick:
                drive('DOWN 100 200', frames=1)
                for _ in range(a.partner_left):
                    drive('LEFT 100 200', frames=1)
            drive('A 150 300', frames=1)
        stem = os.path.splitext(a.out)[0]
        for i in range(40):
            drive('A 150 300' if i in (3, 6) else 'RIGHT 10 10', frames=1, out='%s_%02d.png' % (stem, i))
        print(stem + '_NN.png')
        return
    until(lambda s: green(s, 765, 252) or green(s, 915, 252), 'A 150 300', what='the dummy\'s Tag/Solo prompt')
    until(lambda s: green(s, 915, 252), 'RIGHT 120 200', what='the dummy\'s Solo highlighted')
    drive('A 150 500', frames=2)
    if a.rick:                               # the dummy's cursor starts on the player's cell: back to Marduk
        drive('DOWN 100 200', frames=1)
        for _ in range(3):
            drive('LEFT 100 200', frames=1)
    if a.dummy_rick:                         # ... from Marduk's to Rick's
        for _ in range(3):
            drive('RIGHT 100 200', frames=1)
        drive('UP 100 200', frames=1)
    drive('A 150 500', frames=4)
    for _ in range(a.stage_right):           # one stage a press; the list animates, so wait a few frames each
        drive('RIGHT 100 300', frames=4)
    drive('A 150 2000', frames=25, out=a.out)
    print(a.out)


if __name__ == '__main__':
    main()
