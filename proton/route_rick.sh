#!/bin/sh
# A Practice fight: Rick (his own cell, TTT2_RICK=1, development exe) vs Marduk on the German stage; saves a screenshot.
#   proton/route_rick.sh [screenshot.png]
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(realpath -m "${1:-$HERE/pfx/pfx/drive_c/ttt2/port/rick.png}")
D="python3 $HERE/drive.py"
TTT2_RICK=1 STOP=select "$HERE/route_marduk.sh" tekken_recomp_linux.exe >/dev/null      # on Marduk (cell 16)
for i in 1 2 3; do $D "RIGHT 100 200" --frames 1 >/dev/null; done                        # column 19
$D "UP 100 200" --frames 2 >/dev/null                                                   # Rick's cell (top row)
$D "A 150 500" --frames 3 >/dev/null
$D "RIGHT 120 300" --frames 1 >/dev/null; $D "A 150 800" --frames 2 >/dev/null          # the dummy: solo
$D "DOWN 100 200" --frames 1 >/dev/null
for i in 1 2 3; do $D "LEFT 100 200" --frames 1 >/dev/null; done                         # Marduk
$D "A 150 800" --frames 4 >/dev/null
for i in 1 2 3 4; do $D "RIGHT 100 200" --frames 1 >/dev/null; done                      # Germany
$D "A 150 2000" --frames 30 --timeout 300 --out "$OUT"
