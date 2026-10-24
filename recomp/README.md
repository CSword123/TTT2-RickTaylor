# TTT2-Recomp integration

Target: [thatcalikid760/TTT2-Recomp](https://github.com/thatcalikid760/TTT2-Recomp) at commit `b35355f` (v0.2.0). It is a
fork of shihabal3amri's Xbox 360 port: a XenonRecomp static recompilation for Windows, built with MSVC + clang-cl.

```
python3 recomp/install.py <TTT2-Recomp checkout>     # apply patches/ (refuses other commits without --force)
```

Then build the recomp as its `BUILDING.md` says (Windows only).

## Game files it needs

- The *Tekken Tag Tournament 2 (USA, Europe)* Xbox 360 disc image. The installer checks only the SHA-1 of
  `Default.xex` (`a942090b7c293d0ce63346ed8a2974448135d0dd`, retail 0.0.0.2), not the region. The same disc was
  sold in North America and PAL regions.
- Title Update 3: `TU_174Q22P_0000008000000.00000000000O2` (title `4E4D0859`). The patched image must have SHA-1
  `66adbc1a7744ec840a3ae8e51f8aeb677140d789`.

## How the recomp reads data

- `kernel_io.cpp` `ResolvePath` maps guest paths (`game:\`, `d:\`, `\Device\Cdrom0\`) to `TTT2_VFS_ROOT` (the
  installed `game\` folder), and `update:\` to `<VFS_ROOT>/update`.
- Assets are not separate files. `nrfo.bin` (u32 count, then (u32 offset, u32 size) per archive) has one record
  per `dataNNN.bin`. Each record is made of boxes (u32 size, char[4] kind): `ofsi` holds (u32 name hash, u32 tag)
  pairs and `ofsd` holds the u32 offsets into the archive.
- Title Update 3 is an override layer: the game reads `update:\nrfo.bin` first, and `data100.bin` (expanded) +
  `data100.ofs` replace disc assets by hash. Rick's files can go in the same way.
- On the disc, 26 of the 42 archives are `0x0FF512ED` LZX containers, the same format as Splatterhouse
  (`ttt2rick/common/xlzx.py`). The installer expands them.

## Patches

| Patch | What it does |
|---|---|
| `0001-mod-overlay.patch` | `TTT2_MOD_ROOT` (installed default: `mods\` next to the exe). A file at `mods\<path>` is served instead of `game\<path>`, and `mods\update\<path>` instead of the update's. Directories are never shadowed, and an empty or unset root turns it off. The logic is unit-tested standalone; the full recomp has not been built with it yet (Windows only). |

## Hooking game code

The generated C++ defines every game function as a weak `sub_XXXXXXXX` alias of `__imp__sub_XXXXXXXX`. A strong
`PPC_FUNC(sub_XXXXXXXX)` in a `.cpp` under `port/src/runtime/kernel/` takes over every direct and table call.
CMake globs that folder, and the original stays callable as `__imp__sub_XXXXXXXX`. `diag_hooks.cpp` uses this
pattern. The character loader (roster slot, Rick's files in place of Marduk's, Marduk's moveset) will be built
from such hooks. Their addresses are only valid for the TU3 image above, which is why `install.py` pins the
commit.
