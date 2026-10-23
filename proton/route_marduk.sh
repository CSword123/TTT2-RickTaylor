#!/bin/sh
# Start the game under Proton and drive it to a Practice fight as Marduk (solo, vs Marduk) on the German stage, then
# save a screenshot. Assumes a save and profile already exist (the first run asks more questions: see README.md).
#   [STOP=menu|select] [AT_MENU=<command>] proton/route_marduk.sh [exe name in the install folder] [screenshot.png]
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
EXE=${1:-Tekken Tag Tournament 2.exe}
OUT=$(realpath -m "${2:-$HERE/pfx/pfx/drive_c/ttt2/port/fight.png}")
D="python3 $HERE/drive.py"
cd "$HERE/install/Tekken Tag Tournament 2"
rm -f "$HERE/pfx/pfx/drive_c/ttt2/port/fbdump.bmp"
case "$EXE" in
    tekken_recomp*)     # a development build is a console program: its log goes to dev.log next to the exe
        TTT2_FBDUMP=1 "$HERE/run.sh" cmd /c "$EXE 2> dev.log" > "$HERE/game.out" 2>&1 & ;;
    *)  TTT2_FBDUMP=1 "$HERE/run.sh" "$("$HERE/winpath" "$EXE")" > "$HERE/game.out" 2>&1 & ;;
esac
$D --frames 3 --timeout 120 >/dev/null
for p in "START 150 1500" "START 150 1500" "START 150 2500" "START 150 2500"; do $D "$p" --frames 3 >/dev/null; done
$D "A 150 3000" --frames 6 >/dev/null                                   # profile
$D "A 150 3000" --frames 8 >/dev/null                                   # auto-save notice
[ "${STOP:-}" = menu ] && exec $D --frames 1 --out "$OUT"             # STOP=menu: stay at the main menu
[ -n "${AT_MENU:-}" ] && sh -c "$AT_MENU"                               # AT_MENU=<command>: run it at the main menu
$D "DOWN 120 300" --frames 1 >/dev/null; $D "A 150 500" --frames 4 >/dev/null   # Offline Mode
for i in 1 2 3 4 5; do $D "DOWN 120 200" --frames 1 >/dev/null; done
$D "A 150 500" --frames 5 >/dev/null                                    # Practice
$D "RIGHT 120 300" --frames 1 >/dev/null; $D "A 150 500" --frames 3 >/dev/null   # solo
for i in 1 2 3 4 5 6; do $D "RIGHT 100 200" --frames 1 >/dev/null; done # Jun -> Marduk
[ "${STOP:-}" = select ] && exec $D --frames 1 --out "$OUT"           # STOP=select: stay on Marduk at the select screen
$D "A 150 500" --frames 2 >/dev/null
$D "RIGHT 120 400" "A 150 800" --frames 2 >/dev/null                    # the dummy: solo, Marduk
$D "A 150 800" --frames 4 >/dev/null
for i in 1 2 3 4; do $D "RIGHT 100 200" --frames 1 >/dev/null; done    # Germany, Historic Town Square
$D "A 150 2000" --frames 16 --timeout 180 --out "$OUT"
