# TTT2 Rick Taylor

Rick Taylor from Splatterhouse (2010) as an added fighter in Tekken Tag Tournament 2, running on
[thatcalikid760/TTT2-Recomp](https://github.com/thatcalikid760/TTT2-Recomp), the Xbox 360 static recompilation for
Windows. He starts on Marduk's moveset, and Splatterhouse moves are added over time.

This project ships no game data. It is a converter that reads the player's own Splatterhouse and TTT2 (Xbox 360)
files, plus patches for the recomp.

## Status

| Step | State |
|---|---|
| Splatterhouse `0x0FF512ED` container (XMemCompress LZX) | **done**: `ttt2rick/common/xlzx.py`, byte-exact |
| Gamebryo 20.5 NIF: header and the 14 block types the model uses | **done**: `splatterhouse/nif.py`, `nifblocks.py` (every block read exactly) |
| Skeleton, skinned meshes (submeshes, bone palettes), costume switches | **done**: `splatterhouse/rickmodel.py` (bind error 0 on every mesh) |
| Textures (Xbox 360 tiled DXT1/DXT5, PC byte order) | **done**: `ttt2rick/common/x360tex.py` |
| Export in TTT2 space (mm, Y up, facing +Z) + OBJ + PNG, preview renders | **done**: `splatterhouse/extract.py`, `preview.py` |
| Xbox 360 FATX reader (USB `Data0000…` / HDD), to pull Title Update 3 off your console's storage | **done**: `ttt2rick/common/fatx.py` (verified on a real stick: TU3 came out of the System Cache partition) |
| Xbox 360 disc image (XDVDFS) reader | **done**: `ttt2rick/common/xdvdfs.py` (TTT2 disc: `default.xex` SHA-1 matches the recomp's) |
| Recomp: mods-folder file overlay | **done**: `recomp/patches/0001-mod-overlay.patch` (logic unit-tested; full build pending, Windows) |
| Recomp under Proton (Linux): v0.1.9 installer `/silent` install from the ISO + TU3, game boots at 60 fps | **done**: `proton/` (`tekken.img` SHA-1 `66adbc1a…` as required) |
| TTT2 archives (`nrfo.bin`, `dataNNN.bin`, TU3's `update/data100`), names = CRC-32 keys (`mar.nud`) | **done**: `ttt2rick/ttt2/archive.py` |
| TTT2 NUD / NUT / BONE (Petexy's Wii U readers + 360 magics, NUT mips 16-bit swapped) | **done**: `ttt2rick/ttt2/xbox.py`, `petexy/` (MIT); round trip byte-exact on all 3378 BONE, 8563 of 8564 NUD, 7885 of 7892 NUT |
| Marduk (`mar`): body model, 138-bone skeleton, 39 textures, preview | **done**: `ttt2rick/ttt2/extract.py`; 2256 mm tall (Rick 2232 mm: no rescale needed) |
| Rick -> TTT2 body files under Marduk's names: A-pose -> Marduk's T-pose, Marduk's skeleton moved to Rick's joints, skin weights to TTT2 bones, `.nud`/`.nut`/`.bon`, body-only item database | **done**: `ttt2rick/convert/rick.py` (brawler costume, 15 meshes, 6107 vertices, 1.5 MB textures) |
| Install into the title update's overlay archive (`update/data100`), stock recomp exe | **done**: `ttt2rick/ttt2/overlay.py`; in game (v0.1.9 under Proton): Rick replaces Marduk in Practice, fights with Marduk's moves |
| Character loader hooks in the recomp (own roster slot instead of replacing Marduk) | todo |
| Splatterhouse moves (Havok `.hkx` animations -> TTT2 moves) | later |

## Use

```
python3 -m venv .venv && .venv/bin/pip install numpy pillow
.venv/bin/python -m ttt2rick.splatterhouse.extract <splatterhouse assets/data> work/rick
.venv/bin/python -m ttt2rick.splatterhouse.preview <rick.nif> out.png [brawler|berserker]
python3 -m ttt2rick.common.fatx <USB stick mount> tu work/tu3   # Title Update 3 off an Xbox 360 USB stick
python3 -m ttt2rick.common.xdvdfs <TTT2 .iso> sha1 default.xex  # must be a942090b7c293d0ce63346ed8a2974448135d0dd
python3 recomp/install.py <TTT2-Recomp checkout>       # see recomp/README.md
.venv/bin/python -m ttt2rick.ttt2.archive <game folder> find mar.nud mar.nut mar.bon
.venv/bin/python -m ttt2rick.ttt2.extract <game folder> mar work/ttt2/marduk   # Marduk: npz, obj, png, preview
.venv/bin/python -m ttt2rick.convert.rick <game folder> work/rick/brawler work/rick/textures work/ttt2/rick_as_mar
.venv/bin/python -m ttt2rick.ttt2.overlay <game folder> install work/ttt2/rick_as_mar/files   # Rick in Marduk's place
.venv/bin/python -m ttt2rick.ttt2.overlay <game folder> restore                              # Marduk back
```

Debugging single files:

```
python3 -m ttt2rick.common.xlzx <0x0FF512ED file> <out>        # decompress (Splatterhouse or TTT2)
python3 -m ttt2rick.splatterhouse.nif work/rick.nif             # block table
python3 -m ttt2rick.splatterhouse.nifblocks work/rick.nif       # parser check
```

Costume states: `brawler` (15 meshes, 7632 triangles) and `berserker` (8 meshes, 11158 triangles: spikes, forearm
claws, exposed muscle). Rick is 2232 mm tall in his bind pose (an A-pose).

## Layout

- `ttt2rick/common/`: Xbox 360 formats: LZX container and tiled textures (both games), FATX storage and XDVDFS disc images (read-only)
- `ttt2rick/splatterhouse/`: Rick out of Splatterhouse
- `ttt2rick/ttt2/`: TTT2 Xbox 360 formats: archives, NUD/NUT/BONE (`petexy/`: Petexy's MIT readers, vendored)
- `ttt2rick/convert/`: Rick -> TTT2 fighter files
- `proton/`: `run.sh` runs Windows programs with Steam's Proton in a private prefix, `drive.py` presses buttons and
  takes screenshots of the running game; see `proton/README.md`
- `recomp/`: patches for TTT2-Recomp and the script that applies them, see `recomp/README.md`
- `third_party/` (git-ignored, reference only): `ttt2-recomp/` is the target at `a60b825`. `petexy-ttt2/` is
  Petexy's Wii U port, kept as a reference for TTT2's NUD/NUT/skeleton formats and its Tekken 7 skeleton retargeting.
- `work/`: files decoded from your own discs (git-ignored)
- `xenia/`: a portable Xenia Canary (Linux), used only to install Title Update 3 (git-ignored, see
  `xenia/README.md`)

## Container format (`0x0FF512ED`)

```
u32 0x0FF512ED | u32 1 | u32 hash
u32 (blocks << 6) | 2
blocks x 20-bit uncompressed size (MSB first), padded to 32 bits
per block: frames of [u16 BE compressed size][LZX bits] (32 KiB out each), one LZX state per block, window 2^17
```

## Rick's model (`characters/rick_havok/xbox360/rick.nif`)

10.6 MB decompressed, 805 blocks. It was exported from `rick_brawler.mb` (Maya 8.5, Gamebryo 2.5).
It contains 42 NiMesh (41 skinned), 42 embedded textures and 89 NiNodes. Switch nodes select the costume state:
`Brawler_Rick` / `Berserker_rick`, damage and gore pieces, and the claws. The chosen child of a switch is shown even
when it is stored hidden (`Berserker_rick` is).

Skeleton, which maps nearly one-to-one onto TTT2's bones:

```
root_jnt > C_lowerTorso > C_midTorso > C_upperTorso > C_neck_01 > C_neck_02 > C_head_01
  {L,R}_clavicle_01/02 > shoulder > deltoid > elbow > forearm > wrist > {thumb,index,mid,ring,pinky}Finger_01..03, weapon
  {L,R}_upperLeg > lowerLeg > ankle > ballFoot
  extras: C_berserkerSpike_01..05, R_walletChain_01..03
```

## Texture format

`NiPersistentSrcTextureRendererData` here: pixel format (4 = DXT1, 6 = DXT5), tiling 1 = Xbox 360 tiled (32x32-block
macro tiles, XGAddress2DTiled), but the DXT blocks are in PC byte order (no 16-bit swap). After the mip table:
`u32 padded (tiled) size, u32 untiled size, u32 faces, u32 platform`, then the tiled data.
