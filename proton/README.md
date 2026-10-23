# Proton (Linux): the recomp's Windows parts

`run.sh <program.exe> [args]` runs a Windows program with Steam's Proton 10.0 (or `PROTON=<path to proton>`) in its
own prefix `pfx/`, outside Steam. `winpath <linux path>` prints the `Z:\...` path Windows programs need.
Everything here except these scripts is git-ignored.

Tested 2026-10-23 with TTT2-Recomp v0.1.9 (`ttt2_setup.exe` from the GitHub release, SHA-256
`4149ce98f5e00f82473c4b3f86d4305b6daae7b31b8965a41ce6c71e9ae72fcf`), Proton 10.0, RX 7800 XT (RADV):

```
proton/run.sh "$(proton/winpath proton/bin/v0.1.9/ttt2_setup.exe)" /silent \
    "$(proton/winpath '<disc>.iso')" "$(proton/winpath work/tu3/TU_174Q22P_0000008000000.00000000000O2)" \
    "$(proton/winpath 'proton/install/Tekken Tag Tournament 2')"
```

Exit 0 in 43 s, 13 GB; `game/tekken.img` SHA-1 `66adbc1a7744ec840a3ae8e51f8aeb677140d789`. The log is
`bin/v0.1.9/ttt2_setup.exe.log`. Then, from the install folder:

```
proton/run.sh "Tekken Tag Tournament 2.exe"
```

It boots, reads `nrfo.bin`, the archives and `update/data100`, and renders at 60 fps on the GPU path. Its log is
`pfx/pfx/drive_c/users/steamuser/AppData/Local/TTT2Recomp/log.txt`; saves and settings are next to it. Discord
"RPC Connect error" lines are expected (no Discord client in the prefix). Stop it with
`WINEPREFIX=proton/pfx/pfx "<Proton 10.0>/files/bin/wineserver" -k`.

`drive.py` steers a game started with `TTT2_FBDUMP=1` (the recomp's scripted-input file and framebuffer dumps in
`pfx/pfx/drive_c/ttt2/port/`): `python3 proton/drive.py "START 150" "A 150 2000" --frames 4` presses, waits for
four new frames and saves the last as `shot.png`. Route to Rick (in Marduk's place): intro START, title START,
profile A (first run: auto-save, create save data, update and unlock notices: A each), main menu DOWN A (Offline),
DOWN x5 A (Practice), RIGHT A (solo), Marduk is the bald fighter right of King in the right half's middle row, A,
RIGHT A (solo dummy), A, stage A. Presses sent while a menu animates are dropped: send them in small steps.

The release exe does not have this project's patches (`recomp/patches/`); those need a source build (Windows).
