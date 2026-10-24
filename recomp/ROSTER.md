# Rick's own roster slot (work in progress)

Goal: Rick as an added fighter with his own select-grid cell (so he can team with Marduk), on Marduk's moveset,
in a source build of TTT2-Recomp. Petexy's Wii U port does this (`third_party/petexy-ttt2/docs/ARCHITECTURE.md`,
"Added fighters") with ~40 overrides of game functions; their Wii U addresses have to be found again in the Xbox 360
image (`re/decrypted/Default_patched_tu3.bin` = the installer's `game/tekken.img`, loaded flat at 0x82000000).

## Building on Linux

`recomp/linux/build.sh <checkout> <xwin sysroot>`: XenonRecomp built natively, C++ generated (312 files, 331 MB;
acceptance check passes), FFmpeg configured and the exe built with clang-cl + lld-link against an xwin splat of the
Windows SDK / MSVC CRT (`recomp/linux/clang-cl-xwin.cmake`). Works (2026-10-23): the Linux-built `tekken_recomp.exe` (TTT2_LOCAL_SAVES=ON, PPC -O1, like the release) boots under
Proton, loads the existing save and plays a Practice fight with Rick in Marduk's place exactly like the v0.1.9 release.
Rebuilding after a runtime change takes about 20 s.

## Xbox 360 tables (verified at run time)

| Address | What |
|---|---|
| `0x82DD1CC8` | **the fighter code table**, 63 x char*, indexed by internal id: 0-58 the selectable fighters in select order (mar 17, mok 18, jac 19, ..., bcv 56, seb 57, tig 58), 59-62 dek/pra/zka/zkb (practice dummy, empty dummy, Fight Lab mobs). Read by `sub_82331B50` (bound: id < 63). Followed by 7 menu labels and the 59 full names. |
| `0x82DC21B8` | **character records**, 139 x 84 bytes: +0 internal id, +4 costume slot (0/1; 2 = extra), +8 select id (the UI row: `id_to_select`), +12 UI place, +16 sex, +20 a function pointer, +80 enabled. Two per fighter (0-117 = ids 0-58), 118-121 ids 59-62, 122-138 extras. |
| `0x820A24B4` | **motion rows**, 68 x {moveset key (COM, data006), move list key (MVLT), motion pack key (data005)}; row 17 Marduk. Rows 58-65 hold generic `[Zako00]`-`[Zako07]` movesets. |
| `0x8200C8BC` | **select grids** by mode: {cells, count} pairs; cell = 32 bytes {internal id (63 random), 51, up, down, left, right, column, row}. Mode 0 `0x82DC4F60` (46 cells, the two lower rows), modes 1-2 `0x82DC5520` / `0x82DC5CE0` (62 cells: + the top row, columns 3-18), modes 3-5 smaller. Marduk is cell 16. Writing a cell's id at run time (before the select screen opens) changes who that cell picks: tested, id 58 picked Tiger with his portrait, name, model and moves. |
| `0x8200BD24` | a stale 66-entry {code, id} table (`sub_82276158`), with codes z00-z07 no fighter uses: **not** the game's id mapping (it disagrees from id 18 on). |

Functions: `sub_822761A0` record(i), `sub_822762E0` +0, `sub_822762A8` +4, `sub_82276380` +8, `sub_82276310` +12,
`sub_82276408` +80, `sub_82276270` calls +20, `sub_82276348` id -> +8 of its first record, `sub_822763B0` +8 -> record.
`sub_8227A0D8(grids, cell)` the cell's address (grid by the object's +76 mode); `sub_8227AE48(player)` the internal id
under the player's cursor (player +56 = cell index, +33272 = the grids object); `sub_82643A08` the select screen's
per-player update (writes the hovered select id into the screen's data).

## Tools for this work (all from Linux)

- `proton/route_marduk.sh` drives to the select screen (`STOP=select`) or a Practice fight; `AT_MENU=<cmd>` runs a
  command at the main menu (before the select screen copies anything).
- `proton/guestmem.py`: read/write/find/scan the running game's guest memory (`/proc/<pid>/mem`).
- A development exe logs to `dev.log` in the install folder (route_marduk.sh runs it through `cmd /c`).
- `port/src/runtime/kernel/rick_roster.cpp` (in the checkout; to become a patch): `TTT2_ROSTER_TRACE=1` logs the
  record accessors and the cursor's fighter, each distinct (function, argument, caller) once.
- Write watch: `echo <guest addr> > pfx/pfx/drive_c/ttt2/port/watch.txt` (page protection; works under Wine) logs each
  change with host return addresses; `port/tools/rva2sym.py` on `build-linux/tekken_recomp.map` names them. The
  debug-register watch (`TTT2_DATAWATCH`) crashes the game under Wine.

## Plan: Rick as a new fighter (Petexy's design, Wii U -> Xbox 360)

There is no spare fighter in the title (ids 0-62 are all used), so Rick gets internal id 64, records 140/141 and his
own grid cell, like Petexy's added fighters (`third_party/petexy-ttt2/runtime/src/title/roster.cpp`, 68 overrides;
docs/ARCHITECTURE.md "Added fighters"). For Versus/Practice with a team including Marduk, the needed ones:

1. Registration: Rick's code (`ric`) and file keys into the title's key registry and chara master after the title
   registers its own (Wii U `sub_065C3128`).
2. Records: the accessors above answer records 140/141 (Wii U `sub_033D502C`, `sub_033D504C`, `sub_033D5064`, field
   readers, `sub_033D5108`, `sub_033D512C`), and "can be picked" for id 64 (`sub_033D52B4`).
3. Code and motion row readers: `sub_82331B50` and the loader's code read (Wii U `sub_044BE1EC`) for id 64; the motion
   row: a spare row (58, a Zako row) keyed to Rick's moveset (Marduk's), move list and motion pack (`sub_075DA0C8`).
4. Picks and the match set-up: the select pick (`sub_033E2530`, `sub_033E265C`), the side/ids readers
   (`sub_06EEAEE4`, `sub_04FA571C`) and the setters that cap ids at 62.
5. Select screen: a grid cell for id 64 (a copy of the grid with one more cell, the 0x8200C8BC pointers moved to it),
   UI position/portrait/name (`sub_06F0A484`, `sub_06F0A4A4`, `sub_033D555C`, `sub_06EFA17C`, `sub_06F046D4`,
   `sub_06F0449C`), the costume chooser (`sub_0580D690`, `sub_02669380`, `sub_033E3460`).
6. Voice: one of the free bank ids bound to Marduk's banks (`sub_07A5CAC8`, `sub_07A5CAA4`, `sub_07A5D01C`,
   `sub_079E5B1C`, `sub_079E5D64`, `sub_0796F4C0`, `sub_0796F218`).

Each Wii U function's 360 counterpart is found from the data it touches (as the record accessors were) and checked
with the trace hooks.

## Status (2026-10-23)

Working (`TTT2_RICK=1`, `recomp/runtime/rick_slot.cpp`, files from `ttt2rick.convert.slot`): Rick has his own cell
(top row, right of Violet, in the 62-cell grids of modes 1 and 2), internal id 64, records 140/141, motion row 58,
code `ric` registered in the key registry and chara master. Practice: Rick (picked from his cell) vs Marduk loads and
fights; Rick uses Marduk's moveset. Overrides so far: the chara master/registry builders (`sub_82468AD0`,
`sub_8246A054`), the record accessors, the per-id record lists, the pick gate (`sub_82276760`), the player set-up
(`sub_82276628`), the pick (`sub_8227DC40`, which tests the id's bit in a 64-bit mask), the loader's code read
(`sub_82331B50`) and a 63-bit bitset (`sub_82554F08`).

Still open: the select screen shows Marduk's portrait/name for Rick's cell (UI tables by id), a few bounds asserts
during the fight load are ignored by the runtime (`sub_8255C108`, `sub_82584ED0`, `sub_8225D460`: tables indexed
by id, to answer with Marduk's row), tag teams with Rick + Marduk not yet tried, voice is Marduk's.

### Portraits (from the user's picture `work/art/rick_taylor.png`)

`ttt2rick.convert.portrait` makes Rick's two big portraits (356x612, red / blue mirrored) in the game's frames and
writes them as `ric/portrait_1p.nut` / `ric/portrait_2p.nut`. The game shows portraits two ways:
- by key: `sub_8262B9A0` reads a 59 x 2 key table (`0x820CD408`, by UI row); `rick_slot.cpp` lends Rick's keys to
  Marduk's row while it runs for Rick (screens after the select; not yet seen: Practice has no VS screen).
- by layout label: the 2D layouts (LMB, data007) jump per-fighter sprites to labels `<kind>_<code>`
  (`chara_face_`, `chara_name_s_`, `face_`, `p<n>_chara_waku_`, `chara_face_yoko_`, ...). `ttt2rick.convert.layouts`
  adds Rick's labels and pictures to the 58 layouts with Marduk's; `rick_slot.cpp` renames Marduk's label to Rick's
  in `sub_82B62BE8` (a sprite's jump to a label by name) while the last UI-row question (`sub_82276348` by id,
  `sub_82276380` by record) was about Rick. Loading and VS screens: done.
- the fights' HUD: container `7C476BDE` by numbers from `0x82DDD2F0` (59 x {name, face 1p, face 2p}); Rick's three are
  appended as 259-261 (`ttt2rick.convert.hud`) and given for Marduk's in `sub_823D11B8` the same way. Done.
- the select screen's big portrait: `sub_8262BEE0` lists container `6CCDFC60`'s frames per player (vectors {first,
  last, end} at lister +4 and +24, by UI row); `sub_8262B2D0(lister, row, slot = player * 2 + member)` shows one.
  Rick's two frames are appended as 118/119 (`ttt2rick.convert.portrait`); while a slot whose member is Rick (its
  record at player object +348/+352, before a pick the cursor's id from `sub_8227AE48`; player object
  `*(*(screen + 148) + 48 / 56)`, screen from `sub_826409E0`) is drawn, Marduk's row holds Rick's frame. Done.

### Stance (not working yet)

`ttt2rick.convert.idle` retargets Splatterhouse's `combatidle` (Havok, `ttt2rick.splatterhouse.hkx`) to the TTT2
skeleton as a raw animation and writes `RIC2` = Marduk's motion pack with body animation 0x26 (the standing move
`Va_sKAM00_`'s `ikvt_kamae010`, played as 0x4026) replaced. Channel 1 (the root) is multiplied by the skeleton's
scale in game (checked: Marduk's stance's feet stand on the floor only so). Not in use: Rick still shares Marduk's
motion row 17. Findings (2026-10-23):
- the player set-up (`sub_82276628`, run with Marduk's record) copies the record's id and motion row into the player
  (+84, +80) and loads the motion data (`sub_8231C718`) before returning; the game reads the motion-row table only at
  boot (data watch on rows 17 and 66 after boot: no reads) and keeps loaded keys in resource nodes;
- motion row 66 is used by ids 59/60 and by the set-up for id 49; rows 57, 58, 60-65 are used by no record;
- loading Rick through row 65 (Marduk's record carrying row 65 during his set-up) made him kick and jump on his own
  from the round's start, with any motion pack (even Marduk's, byte for byte) and the `RIC1` moveset copy or
  Marduk's: the row itself, not the data. Rows 58-65 are the mob (`Zako`) rows;
- in memory no MOTA has Marduk's 606 animations (mid-fight: MOTAs of 1875, 448, 684), so the loaded animations are
  not the pack file as it is. Next: find where a player's animation id (0x4026) is resolved to its data, and give
  Rick's player his stance there.
