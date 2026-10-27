"""Drive the game to a VS Battle (two players: the second one's presses are drive.py's P2+...) and save the frames from
the stage select on (the VS screen, the intro, the fight's start).

python3 proton/route_vs.py --p1 jen,hwo --p2 mar,jen [--out vs.png]       (one code: solo; two: tag)

The fighters are select cells by code (CELLS: Rick and Jennifer at the top row's columns 19 and 20, TTT2_RICK=1).
Each player's cursor starts on its own cell (player 1: Jun, player 2: Heihachi) and stays on a picked cell. Frames are
saved as <out>_NN.png. Started with TTT2_RICK=1 (and the caller's environment: TTT2_RICK_TRACE etc.).
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from route import PORT, drive  # noqa: E402

CELLS = {'jun': (10, 1), 'hei': (12, 1), 'mar': (16, 1), 'leo': (17, 1), 'hwo': (18, 1), 'edd': (19, 1),
         'lee': (20, 1), 'vio': (18, 0), 'ric': (19, 0), 'jen': (20, 0)}
START = {'': CELLS['jun'], 'P2+': CELLS['hei']}


def press(who, button, frames=1, out=None):
    return drive('%s%s 120 250' % (who, button), frames=frames, out=out)


def go(who, here, target):
    col, row = here
    tcol, trow = CELLS[target]
    if row == 0:
        press(who, 'DOWN')
    for _ in range(abs(tcol - col)):
        press(who, 'RIGHT' if tcol > col else 'LEFT')
    if trow == 0:
        press(who, 'UP')
    elif trow == 2:
        press(who, 'DOWN')
    return (tcol, trow)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--p1', required=True)
    ap.add_argument('--p2', required=True)
    ap.add_argument('--frames', type=int, default=24)
    ap.add_argument('--p2-button', default='A', help="the button player 2 confirms its fighters with (TTT2 picks the "
                    "costume by it: try Y for costume B)")
    ap.add_argument('--out', default=os.path.join(PORT, 'vs.png'))
    a = ap.parse_args()
    teams = {'': a.p1.split(','), 'P2+': a.p2.split(',')}
    env = dict(os.environ, TTT2_RICK='1')
    subprocess.run([sys.executable, os.path.join(HERE, 'route.py'), '--stop', 'menu'], env=env, check=True,
                   capture_output=True)
    press('P2+', 'START', 2)                         # the second controller joins
    press('', 'DOWN')
    press('', 'A', 3)                                # Offline Mode
    press('', 'DOWN')
    press('', 'DOWN')
    press('', 'A', 4)                                # VS Battle
    press('', 'START', 2)
    press('P2+', 'START', 3)
    press('', 'LEFT')                                # battle positions: player 1 left, player 2 right
    press('P2+', 'RIGHT')
    press('', 'A')
    press('P2+', 'A', 3)
    press('', 'A', 4)                                # "Exiting player select. Continue anyway?"
    for who, team in teams.items():                  # Tag (highlighted first) or Solo
        if len(team) == 1:
            press(who, 'RIGHT')
        press(who, 'A', 2)
    here = dict(START)
    for member in range(2):
        for who, team in teams.items():
            if member < len(team):
                here[who] = go(who, here[who], team[member])
        stem = os.path.splitext(a.out)[0]
        drive(frames=2, out='%s_pick%d.png' % (stem, member))
        for who, team in teams.items():
            if member < len(team):
                press(who, a.p2_button if who == 'P2+' else 'A', 2)
    drive(frames=3, out='%s_stage.png' % stem)
    press('P2+', 'A')                                # player 2 picks the stage in VS Battle
    for i in range(a.frames):
        drive(frames=1, out='%s_%02d.png' % (stem, i))
    print(stem + '_NN.png')


if __name__ == '__main__':
    main()
