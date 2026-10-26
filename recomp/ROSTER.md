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
| `0x820A24B0` | **motion rows**, 68 x {motion pack key (MOTA pack, data005), moveset key (COM, data006), move list key (MVLT)}, read by `sub_82590690(holder, row)` when a fighter loads (row 66: two keys of its own); row 17 Marduk = {`C903BD27` (684 animations), `7491FE62`, `68A7CEF7`}. Rows 58-65 hold generic `[Zako00]`-`[Zako07]` movesets. Until 2026-10-24 this file put the table at `0x820A24B4`, one word late, so every "motion pack" key was the next row's (`75F7BE7E` is Jack-6's). |
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

### Stance (working, 2026-10-24)

`ttt2rick.convert.idle` retargets Splatterhouse's `combatidle` (Havok, `ttt2rick.splatterhouse.hkx`) to the TTT2
skeleton as a raw animation and writes `RIC2` = Marduk's motion pack (`C903BD27`) with body animation 0x26 (his
guard stance, which his standing move `Va_sKAM00_` plays as 0x4026) replaced. Channel 1 (the root) is multiplied by
the skeleton's scale in game. Rick has motion row 57 (no record uses it; not a Zako row), written by `rick_slot.cpp`
as {`RIC2`, `RIC1`, Marduk's move list}; the player set-up (`sub_82276628`, run with Marduk's record) loads the
motion data by the record's row, so Marduk's record carries row 57 during Rick's set-up. In Practice Rick stands in
his Splatterhouse stance, Marduk's moves play from it, and the Marduk opponent keeps his own.

The earlier failures (2026-10-23) came from the table's wrong base: the stance was built on Jack-6's pack, and a
row's motion key was written into the next row, so Rick on row 65 ran the mob row's own animations (he kicked and
jumped on his own). The row number itself is not special.

Guard (2026-10-24): Splatterhouse's `block` (his held block), 40 frames at 60 fps, is appended to `RIC2`'s body
MOTA as animation 684 (moves play it as `0x42AC`); `ttt2rick.convert.slot` gives it to the 15 standing guard moves
of `RIC1` (`sGrd_*` playing the common `Bco_gurd_*`, ids `0x8xxx`, which every fighter shares and so stay as they are).
A blocked attack runs the defender's own move of that number, so any attacker's blocked hits show Rick's block; the
guards go back to the stance at their frame 19. Checked in Practice with the dummy on Controller (Action Settings 1;
player 2 presses START to take it): Marduk's blocked jabs put Rick in his block, then back in his stance. Crouching
guards (`cGrd_*`) are still the common ones.

Feet: a skeleton's parameters 1-4 are the ankles' and toes' heights over the soles (times its scale): every title
skeleton has its ASHI / TSUMASAKI joints there (a few mm lower in some: shoe soles). Rick's are his own, with his feet
flat as in his bind pose and his stance (126.9, 59.8; `ttt2rick.convert.rick` foot_heights), not the T-pose's (153.5,
65.5: its feet are aimed down like Marduk's, the ankles higher over the toes' tips). Not yet seen on uneven ground.

Floating feet (fixed 2026-10-24): the stance's root had been moved by Havok's root offset from its reference, from the
bind root; that bind root carries `convert.rick`'s 100.5 mm lift (straightened legs stood on the floor), so with his
own bent legs his soles floated ~7-10 cm. The root now gets the mesh's own transform (`convert.idle`, step 3); both
animations' ankles are at 156 mm (Splatterhouse's, soles on the floor), as Marduk's are at his 156.

Neck (fixed 2026-10-24): the chest channel (MUNE1, spread by the game over MUNE1/MUNE2) took `C_midTorso`'s rotation,
but his hunch bends at `C_upperTorso` (20 degrees in combatidle), so the chest stayed upright under a hunched neck and
head and the skin from the back of the head to the shoulders stretched into a flat sheet. It now takes the upper
torso's (`convert.idle` DRIVERS); checked in Practice from several angles.

Neck colour (2026-10-25): the neck mesh (`rick_neck`) is painted from the mask's texture, whose skin was graded to the
body's median like every skin texture; at the seam the body is darker and redder than its median, so the upper neck
came out 20-33% lighter and greyer over a dark wedge of the body. `convert.rick` seam_scale now grades the mask's
saturated skin on to the body's colour at the 29 seam vertices (x 0.79 / 0.69 / 0.65), leaving the mask's bone white.
Checked at RenderScale=200 with `TTT2_FB_NATIVE=1` (C:/ttt2/port/fb_native.bmp at 2560x1440): much closer up.

Tag teams (2026-10-25, Arcade): picking the partner used to end "Rick is picked" (`rick_slot.cpp`, the member byte
fix), so the copies of his byte stayed capped at 62 and the VS and promotion screens showed row 0 (Paul) for him. Rick's
picked member bytes are now kept one by one. With 64 then reaching the save data's per-fighter entry
(`sub_825550C8`, Tag25SaveData, at the pick) the game wrote out of range and froze: that entry is Marduk's for him.
Checked: Rick + Hwoarang shows both on the VS screen. Rick + Marduk shows Rick only (one panel for P1: both members
have Marduk's UI row; not yet looked into). `proton/route.py --rick --arcade --tag [--partner-left N]` drives it.

Arcade continue (2026-10-25): after a lost match the save data's per-fighter tables and the profile's fighter
records (EachFighterInfoCS, Array<, 63>) were indexed with Rick's 64; the failed checks (the title's store to
address 0, which the runtime ignores) left the save update broken and the next load after a continue never ended.
sub_82659F48 (profile records), sub_82584E88, sub_82585230, sub_82585590 (table accessors) now take Marduk's id for
him, as sub_82584ED0 and sub_825550C8 already did: his results count as Marduk's until he has save entries of his
own. Checked: Arcade loss, continue, back to the select screen.
Customize mode: its character grid is Xtal script, compiled from source at load: the title update's menu file
0xB43EB78F defines global::CharacterSelectCursor (GetFighterID: a 3 x 22 table chr_line; IsFocusableCharacter refuses
top-row x 0-2 and 18-21). ttt2rick.convert.menus puts Rick at x 18 (right of Violet) with same-length text edits, and
the cursor reaches him, but choosing him hangs the menu in his costume panel's load (sub_8272A5F0), so it ships only
with RICK_CUSTOMIZE=1. Its cursor position is mirrored in a menu variable (0x0086C4E4 in one run).

Downed Rick could not be hit (fixed 2026-10-25): sub_822FB4F8 (player r3) takes a per-fighter body pointer by id
from two 64-entry tables (0x82DD0A68; 0x82DD0B68 in down states 12-13) without a bound, so Rick's 64 read the second
table's first entry. Found by bisecting, in game, wrappers that show Marduk's id for Rick in each of the 445
functions of 0x822-0x826 that read player +84 (Rick's files as Marduk's id 17 were hittable; leaving +84 at 17 for
Rick hides him as player 1). The hook shows Marduk's id while that one function runs. Practice "Action on the floor:
OFF" keeps a dummy down for such tests.
P2 portrait (fixed 2026-10-25): the Practice dummy's pick stores the capped 62 without sub_8227CFC0; sub_8227DC40
now marks Rick picked on any pick, so the member bytes get 64 back.

Still open: only the standing and guard animations are his. Marduk's moves start and end in Marduk's guard (the game blends
between them); other idles (crouch, the walk cycles, tag-in) are Marduk's.

## Jennifer: a second added fighter (2026-10-26)

`rick_slot.cpp` now holds a table of added fighters (kFighters), each with its own id, records, motion row, code,
grid cell, portrait frames and HUD numbers; every hook asks which added fighter (if any) an id, record or row is.
TTT2_RICK=1 turns them on, TTT2_JEN=0 leaves Jennifer out.

| | Rick | Jennifer |
|---|---|---|
| id, records | 64, 140/141 | 65, 142/143 |
| motion row | 57 {RIC2, RIC1, Marduk's move list} | 58 (a Zako row: Fight Lab's Zako00 loses it while she is on) {JEN2, JEN1, Marduk's move list} |
| code, body | `ric`: ric.nud/.nut/.bon/.xml on Marduk's skeleton | `jen`: jen.* on Nina's skeleton, with Nina's spring-bone file nin.mop (registry type 3; types 0-4 are nud, nut, bon, mop, havok.xml) |
| grid cell (modes 1, 2) | 62: top row column 19 | 63: top row column 20 (above Lee) |
| select portraits (6CCDFC60) | frames 118/119 (bloody 120/121) | 122/123 |
| HUD (7C476BDE) | 259-261 | 262-264 |

Both have Marduk's records otherwise (UI row 18, sex, +20 function), his voice and his save entries.

- The member bytes: the title's copies cap an id at 62, and with two added fighters a capped 62 has to be told apart.
  The picks are kept per (player, member) (g_picks, set at sub_8227CFC0 and sub_8227DC40; a select cursor has its
  player at +320 and the members picked so far at +340), and sub_822815E0's side (r3 - 640) is matched against the
  players' sides, `*(*(*0x82E6C5A8 + 256) + 60 + 4 * player)` (sub_82653478).
- The VS screen (sub_826353D8, four slots: p1/p2 _chara_waku_ main/sub) hides a side's second panel when
  sub_82634870 calls the side solo, which it decided by the members' UI rows being equal: a team of Marduk and an
  added fighter, or of two added ones, showed one panel (the "Rick + Marduk shows Rick only" item). It is now solo
  only when both members are the same fighter. Checked in VS Battle: Jennifer + Hwoarang vs Marduk + Jennifer,
  Rick + Jennifer vs Jennifer + Rick, Rick vs Jennifer solo; in Arcade: Jennifer + Marduk (promotion screen too).
- The Practice dummy's tag picks use grid mode 0 (the two lower rows only), so no top-row fighter (Violet, Tiger,
  Rick, Jennifer) can be the second-player team there; VS Battle has them. `proton/route_vs.py` drives VS Battle
  (the second controller joins with P2+START, then VS BATTLE is enabled in the Offline menu).
- Select grid icons: the title's icons are the fighter cut to the panel's frame, with the frame's black edges and
  white line drawn over him (art.in_frame, from the empty panel shape every panel shows); Rick's had covered them.
  The right grille is shortened by a column for Jennifer's cell (art.Layout.shorten_spacer: texels of the plain
  perforation cut out before its bevelled edge).

## Moves on the buttons' limbs (2026-10-26)

ttt2rick.convert.attacks (see its docstring): 2, 2,2, 2,2,1 is Splatterhouse's right-hand X chain (right haymaker on
Marduk's 2 at i12, right backhand, the 360 punch with the left arm), a natural 3-hit combo in game (12 + 12 + 19 at
Practice's 120%); b+1 and its strings are Marduk's again. 3+4 is Splatterhouse's RT crouch (offbalance_idle, idle.py
CROUCH: Marduk's crouch loop and its way in and out replaced); from it 1 is the running ram (RT+Y, left shoulder,
active 16-26: at 16-19 it whiffed while still closing in), 2 the sweeping punch (RT+X, right fist, a mid launcher)
and 1+2 Marduk's takedown with Splatterhouse's lunge (RT+B, tackle_miss), into his mount. Each move's striking limb
at its hit frame and its hitbox bones (TE_R = 9, UDE_R 8, KATA_L 11, UDE_L 12, TE_L 13) were checked against the
buttons: 1 left arm, 2 right arm. Jennifer gets all of it through Rick's moveset (JEN1) and motion pack (JEN2).

Select screen with two of Rick, Jennifer and Marduk in one team (2026-10-26): the update (sub_82643A08) treats two
members with the same UI row as one fighter (it skips or hides the second, and redraws a member only when its row
changes), and all three have row 18. While the second member is chosen, rick_slot.cpp draws it itself after the update
(SelectSecondMembers: big portrait, frame and face labels); once both are picked, the second member's record questions
answer Steve's row 17 (kAliasRow) and Steve's labels and portrait become the member's. Labels on the select screen are
renamed by the member their sprite belongs to (`_main`/`_sub`, `p1`/`p2`), not by the last fighter asked about. Left
over: the rank bars' small face icons can show the other member, and a picked second member's bar reads "Beginner"
(Steve's row; it showed an empty bar before).
