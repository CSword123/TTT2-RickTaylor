# TTT2 Rick Taylor

Rick Taylor from Splatterhouse (2010) as a new fighter in Tekken Tag Tournament 2, with his own Splatterhouse moves,
his voice and Mirror Rick as his second costume. Jennifer Willis can come along as a second added fighter.

It is a mod for the TTT2 PC recomp: [thatcalikid760/TTT2-Recomp](https://github.com/thatcalikid760/TTT2-Recomp), or
[shihabal3amri's port](https://github.com/shihabal3amri/tekken-tag-tournament-2-pc) it is a fork of. Nothing from
either game comes with it: the installer makes Rick from **your own Splatterhouse disc image** and Marduk's files in
your TTT2 install.

## You need

- The TTT2 recomp, installed with its own installer (with Title Update 3), and run at least once.
- Your Splatterhouse disc image: Xbox 360, USA (`Splatterhouse (US) (Xbox 360).iso`).
- Python 3.9 or newer, with numpy and Pillow: `python -m pip install -r requirements.txt`
- [FFmpeg](https://ffmpeg.org/download.html), with `ffmpeg` on the PATH (Windows: `winget install ffmpeg`; Linux:
  your distribution's `ffmpeg` package). The installer uses it to match Rick's voice to the game's loudness.

## Install

```
python install.py
```

It asks for the recomp's folder (the one with its exe and `game` folder), your Splatterhouse disc image, and whether
you want Jennifer and Splatterhouse's blood. Converting takes a few minutes. Or, without questions:

```
python install.py --recomp "C:\Games\TTT2 Recomp" --iso "D:\Splatterhouse (US) (Xbox 360).iso" [--no-jennifer] [--blood]
```

Then start the game as usual. Rick is in the top row of the character select, right of the last fighter, and
Jennifer beside him.

**Linux (Steam / Proton):** the recomp (0.2.0 and later) needs Microsoft's 64-bit `d3dcompiler_47.dll` next to its
exe: Wine's own shader compiler fails some of its shaders and the fighters' bodies are not drawn. It is not in this
zip; copy it from another Windows game that ships it. Then set the game's launch options to

```
WINEDLLOVERRIDES="d3dcompiler_47=n,b;winmm=n,b" %command%
```

so Wine loads that `d3dcompiler_47.dll` and the mod's `winmm.dll` instead of its own. The override only picks which
copy Wine loads: the DLLs themselves must be in the exe's folder.

## Settings

`ttt2rick.ini`, next to the game's exe:

| Line | |
|---|---|
| `rick = 1` | the mod (`0`: the stock game). Change it any time. |
| `blood = 0` | Splatterhouse's blood on Rick's clothes, Mirror Rick's skin and his portraits (`1`). Change it any time. |
| `jennifer = 1` | Jennifer as well (`0`: Rick only). The installer's choice: the select screen's pictures are made with or without her, so to change it run `install.py` again with `--jennifer` or `--no-jennifer` (quick: the disc's files are kept). |

## Uninstall

```
python install.py --recomp "<the recomp's folder>" --uninstall
```

puts the game's files back as they were and takes the mod's `winmm.dll` and `ttt2rick.ini` out.

## How it works

`winmm.dll` is the mod's loader: the game's exe loads it at start. It finds the recomp's table of recompiled game
functions and hooks the ones Rick needs (his roster slot, his select screen pictures, his voice). The fighters' files
go into the game's title update overlay (`game/update/data100`, its originals kept in `game/update/original`). If
something does not load, `ttt2rick.log` next to the exe says why.
