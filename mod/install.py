"""TTT2 Rick Taylor: installs Rick Taylor (and Jennifer Willis) from Splatterhouse (2010) into a Tekken Tag
Tournament 2 recomp: thatcalikid760's TTT2-Recomp or shihabal3amri's port it is a fork of, as installed by their own
installer (the folder with the game's exe and its game\\ folder, Title Update 3 included).

    python install.py                                  asks for the recomp's folder and your Splatterhouse disc image
    python install.py --recomp <folder> --iso <Splatterhouse (US) (Xbox 360).iso> [--no-jennifer] [--blood] [--yes]
    python install.py --recomp <folder> --uninstall    everything back as it was

Needs Python 3.9+ with numpy and Pillow (pip install -r requirements.txt). Nothing of either game comes with the
mod: Rick, Jennifer, his moves and voice are made from your own Splatterhouse disc (the Xbox 360 USA disc, title
4E4D07F0) and Marduk's files in your own TTT2 install. It
1. reads the files it needs straight off the disc image (work/splatterhouse);
2. converts them (work/rick, work/ttt2/...; the same steps as the project's README, a few minutes);
3. installs them into the game's title update overlay (game/update/data100, its originals kept in update/original);
4. puts the mod's loader, winmm.dll, next to the exe, and ttt2rick.ini with your choices.

ttt2rick.ini holds them; rick and blood can be changed there any time, no reinstall needed:
    rick = 1          the mod at all (0: the stock game, with the files still installed)
    blood = 0         Splatterhouse's blood on Rick's clothes, Mirror Rick's skin and his portraits
    jennifer = 1      Jennifer as a second added fighter (0: Rick only): the installer's choice (the select grid's
                      pictures are made with or without her), so run it again with --jennifer / --no-jennifer

On Linux (Proton), Wine loads its own winmm unless told otherwise: set the game's launch options to
    WINEDLLOVERRIDES="winmm=n,b" %command%
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# the mod package (install.py beside ttt2rick/), or the project's own checkout (mod/install.py)
ROOT = HERE if os.path.isdir(os.path.join(HERE, 'ttt2rick')) else os.path.dirname(HERE)
LOADERS = [os.path.join(HERE, 'winmm.dll'), os.path.join(ROOT, 'mod', 'loader', 'build', 'winmm.dll')]
WORK = os.path.join(ROOT, 'work')
SH = os.path.join(WORK, 'splatterhouse')
LOADER_MARK = b'ttt2rick.log'                  # a string only the mod's winmm.dll has
RECORD = 'ttt2rick-install.json'
INI = 'ttt2rick.ini'

# Splatterhouse (2010), Xbox 360: its title id, and the USA disc's default.xex (region free, so the files decide)
SH_TITLE = 0x4E4D07F0
SH_US_XEX_SHA1 = 'df1d0d9b03420b5475afaf536174a386ab547508'
# what the converters read of it, under its data folder: whole folders (every .hkx of Rick's: his stance, attacks,
# run) and files
SH_FOLDERS = ['characters/rick_havok/xbox360', 'characters/jennifer/xbox360']
SH_FILES = ['characters/mirrorrick/xbox360/mirrorrick.nif', 'characters/props/xbox360/walletchain.nif',
            'sounds/soundbanks/xbox360/English(US)/sb_rick_vox.bnk', 'sounds/soundbanks/xbox360/SoundbanksInfo.xml']


def say(*a):
    print(*a, flush=True)


def ask(question, default):
    """yes / no on the console (Enter: `default`)."""
    answer = input('%s [%s] ' % (question, 'Y/n' if default else 'y/N')).strip().lower()
    return default if not answer else answer.startswith('y')


def pick(title, file_types=None):
    """A path from a file dialog when there is a desktop (tkinter), else typed in."""
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        path = (filedialog.askopenfilename(title=title, filetypes=file_types) if file_types
                else filedialog.askdirectory(title=title))
        root.destroy()
        if path:
            return path
    except Exception:
        pass
    return input('%s: ' % title).strip().strip('"')


# ------------------------------------------------------------------------------------------------ the recomp

def recomp_game(folder):
    """The recomp's game folder (its exe's game\\, with nrfo.bin and Title Update 3's update\\data100)."""
    game = os.path.join(folder, 'game')
    if not os.path.isfile(os.path.join(game, 'nrfo.bin')):
        raise SystemExit('%s: no game\\nrfo.bin. Give the folder of the recomp\'s exe (installed with its own '
                         'installer).' % folder)
    if not os.path.isfile(os.path.join(game, 'tekken.img')):
        raise SystemExit('%s: no game\\tekken.img (the TU3 game image the recomp\'s installer makes): install the '
                         'recomp with its own installer first.' % folder)
    if not os.path.isfile(os.path.join(game, 'update', 'data100.ofs')):
        raise SystemExit('%s: no game\\update\\data100.ofs: the recomp needs Title Update 3 installed.' % folder)
    if not [n for n in os.listdir(folder) if n.lower().endswith('.exe') and n.lower() != 'uninstall.exe']:
        raise SystemExit('%s: no exe in it' % folder)
    return game


# ------------------------------------------------------------------------------------------------ Splatterhouse

def open_splatterhouse(path):
    """The disc image (ttt2rick.common.xdvdfs.Iso), once it is Splatterhouse with the files the converters read."""
    from ttt2rick.common.xdvdfs import Iso
    try:
        iso = Iso(path)
        sector, size, _ = iso.lookup('default.xex')
    except (ValueError, KeyError, OSError) as e:
        raise SystemExit('%s: not an Xbox 360 disc image (%s)' % (path, e))
    xex = b''.join(iso.chunks(sector, size))
    title = None
    if xex[:4] == b'XEX2':
        for i in range(struct.unpack_from('>I', xex, 0x14)[0]):
            key, value = struct.unpack_from('>II', xex, 0x18 + 8 * i)
            if key == 0x00040006:                       # execution info: media id, version, base version, title id
                title = struct.unpack_from('>I', xex, value + 12)[0]
    if title != SH_TITLE:
        raise SystemExit('%s: not Splatterhouse (title %s, Splatterhouse is %08X)' % (
            path, '%08X' % title if title is not None else 'unknown', SH_TITLE))
    if hashlib.sha1(xex).hexdigest() != SH_US_XEX_SHA1:
        say('note: this Splatterhouse disc is not the USA one the mod was made with; going on (its files are checked)')
    for p in SH_FOLDERS + SH_FILES:
        try:
            iso.lookup('data/' + p)
        except KeyError:
            raise SystemExit('%s: no data/%s on it (the mod needs the USA disc, with English voices)' % (path, p))
    return iso


def extract_splatterhouse(iso):
    """SH_FOLDERS and SH_FILES into work/splatterhouse/data (files already there of the same size are kept)."""
    wanted = []
    for folder in SH_FOLDERS:
        sector, size, _ = iso.lookup('data/' + folder)
        wanted += [(folder + p, s, n) for p, s, n, is_dir in iso.walk(sector, size) if not is_dir]
    for p in SH_FILES:
        sector, size, _ = iso.lookup('data/' + p)
        wanted.append(('/' + p, sector, size))
    total = 0
    for p, sector, size in wanted:
        dest = os.path.join(SH, 'data', *p.strip('/').split('/'))
        if os.path.isfile(dest) and os.path.getsize(dest) == size:
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest + '.part', 'wb') as f:
            for c in iso.chunks(sector, size):
                f.write(c)
        os.replace(dest + '.part', dest)
        total += size
    say('  %d files (%.1f MB read) in %s' % (len(wanted), total / 1e6, os.path.join(SH, 'data')))
    return os.path.join(SH, 'data')


# ------------------------------------------------------------------------------------------------ conversion

def steps(game, sh, jennifer):
    """The conversion (the project README's commands): (what, module, arguments); Rick's alone without Jennifer
    (the menu layouts without her picture in the select grid)."""
    w = lambda *p: os.path.join(WORK, *p)
    rick_slot, art = w('ttt2', 'rick_slot'), w('ttt2', 'rick_slot', 'art')
    rick = [
        ('Rick\'s body out of Splatterhouse', 'ttt2rick.splatterhouse.extract', [sh, w('rick')]),
        ('Mirror Rick\'s body', 'ttt2rick.splatterhouse.extract',
         [os.path.join(sh, 'characters', 'mirrorrick', 'xbox360', 'mirrorrick.nif'), w('mirrorrick')]),
        # (his wallet chain is Rick's: the extract makes it only from a data folder)
        ('Mirror Rick\'s wallet chain', shutil.copy2, [w('rick', 'walletchain.npz'), w('mirrorrick')]),
        ('Rick on Marduk\'s skeleton', 'ttt2rick.convert.rick',
         [game, w('rick', 'brawler'), w('rick', 'textures'), w('ttt2', 'rick_as_mar')]),
        ('select portraits', 'ttt2rick.convert.portrait', [game, art]),
        ('HUD faces', 'ttt2rick.convert.hud', [game, art]),
        ('menu layouts', 'ttt2rick.convert.layouts', [game, art]),
        ('Rick\'s stance, attacks and run (the longest step)', 'ttt2rick.convert.idle',
         [game, sh, w('ttt2', 'rick_as_mar'), art]),
        ('Mirror Rick on Marduk\'s skeleton', 'ttt2rick.convert.rick',
         [game, w('mirrorrick', 'brawler'), w('mirrorrick', 'textures'), w('ttt2', 'mirror_as_mar'), 'mirror']),
        ('Rick\'s roster slot (moveset, files)', 'ttt2rick.convert.slot', [game, w('ttt2', 'rick_as_mar'), rick_slot, art]),
    ]
    jen = [
        ('Jennifer\'s body out of Splatterhouse', 'ttt2jen.extract', [sh, w('jennifer')]),
        ('Jennifer on Nina\'s skeleton', 'ttt2jen.convert', [game, w('jennifer'), w('ttt2', 'jen')]),
        ('Jennifer\'s motions', 'ttt2jen.motions',
         [os.path.join(art, 'files', 'key_52494332.bin'), os.path.join(rick_slot, 'files', 'ric.bon'),
          w('ttt2', 'jen', 'files', 'jen.bon'), w('ttt2', 'jen', 'files')]),
        ('Jennifer\'s roster slot', 'ttt2jen.slot', [game, w('ttt2', 'jen'), rick_slot, w('ttt2', 'jen_slot')]),
    ]
    rest = [
        ('Rick\'s voice', 'ttt2rick.convert.voice', [game, sh, w('ttt2', 'rick_voice')]),
        ('Customize costume panels', 'ttt2rick.convert.panel', [game, w('ttt2', 'panel')]),
    ]
    return rick + (jen if jennifer else []) + rest


def run(steps_, jennifer):
    log = open(os.path.join(WORK, 'install.log'), 'w')
    for k, (what, module, args) in enumerate(steps_, 1):
        say('[%d/%d] %s' % (k, len(steps_), what))
        log.write('\n$ %s %s\n' % (module if callable(module) else 'python -m ' + module,
                                    ' '.join('"%s"' % a for a in args)))
        log.flush()
        start = time.time()
        if callable(module):
            module(*args)
            continue
        env = dict(os.environ, TTT2_JEN='1' if jennifer else '0')
        r = subprocess.run([sys.executable, '-m', module] + args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                           env=env)
        if r.returncode:
            log.close()
            raise SystemExit('step "%s" failed: see %s' % (what, os.path.join(WORK, 'install.log')))
        say('  done (%.0f s)' % (time.time() - start))
    log.close()


def overlay(game, *args):
    r = subprocess.run([sys.executable, '-m', 'ttt2rick.ttt2.overlay', game] + list(args), cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit('the game\'s overlay (%s): %s' % (' '.join(args[:1]), (r.stderr or r.stdout).strip()))
    return r.stdout.strip()


# ------------------------------------------------------------------------------------------------ the loader

def is_ours(path):
    return os.path.isfile(path) and LOADER_MARK in open(path, 'rb').read()


def write_ini(folder, jennifer, blood):
    with open(os.path.join(folder, INI), 'w') as f:
        f.write('; TTT2 Rick Taylor mod: 1 = on, 0 = off. Change these any time (an environment variable of the same\n'
                '; name in capitals wins: TTT2_RICK, TTT2_JEN, TTT2_RICK_BLOOD).\n'
                '[ttt2rick]\n'
                'rick = 1          ; the mod (0: the stock game)\n'
                'jennifer = %d      ; Jennifer Willis as a second added fighter (0: Rick only). Set by install.py:\n'
                '                  ; to change it, run it again with --jennifer or --no-jennifer\n'
                'blood = %d         ; Splatterhouse\'s blood on Rick (clothes, Mirror Rick\'s skin, portraits)\n'
                % (int(jennifer), int(blood)))


def install_loader(folder):
    loader = next((p for p in LOADERS if os.path.isfile(p)), None)
    if not loader:
        raise SystemExit('no winmm.dll beside install.py (the mod package has one; in the project, build it with '
                         'mod/loader/build.sh)')
    dest = os.path.join(folder, 'winmm.dll')
    backup = None
    if os.path.isfile(dest) and not is_ours(dest):
        backup = dest + '.before-ttt2rick'
        shutil.copy2(dest, backup)
        say('note: a winmm.dll of something else was there: kept as %s (it will not load while Rick\'s does)' % backup)
    shutil.copy2(loader, dest)
    return backup


# ------------------------------------------------------------------------------------------------ commands

def install(a):
    folder = os.path.abspath(a.recomp or pick('The TTT2 recomp\'s folder (with its exe and game folder)'))
    game = recomp_game(folder)
    iso_path = a.iso or pick('Your Splatterhouse (Xbox 360, USA) disc image',
                             [('Xbox 360 disc image', '*.iso'), ('All files', '*')])
    iso = open_splatterhouse(iso_path)
    jennifer = a.jennifer if a.jennifer is not None else (True if a.yes else ask('Jennifer Willis too?', True))
    blood = a.blood if a.blood is not None else (False if a.yes else ask('Keep Splatterhouse\'s blood on Rick?', False))
    say('Splatterhouse: %s' % iso_path)
    say('TTT2 recomp:   %s' % folder)
    os.makedirs(WORK, exist_ok=True)
    say('reading Splatterhouse\'s files off the disc')
    sh = extract_splatterhouse(iso)
    run(steps(game, sh, jennifer), jennifer)
    say('installing into the game (update/data100; its originals stay in update/original)')
    files = [os.path.join(WORK, 'ttt2', d, 'files')
             for d in ('rick_slot',) + (('jen_slot',) if jennifer else ()) + ('rick_voice', 'panel')]
    say('  ' + overlay(game, 'install', *files).splitlines()[-1])
    backup = install_loader(folder)
    write_ini(folder, jennifer, blood)
    json.dump({'winmm_backup': backup, 'installed': time.strftime('%Y-%m-%d %H:%M')},
              open(os.path.join(folder, RECORD), 'w'), indent=1)
    say('\nDone. Rick is in the top row of the character select, right of the last fighter%s.' % (
        ', Jennifer beside him' if jennifer else ''))
    say('Turn the blood on or off in %s any time (Jennifer: run this again with --jennifer / --no-jennifer).'
        % os.path.join(folder, INI))
    if sys.platform != 'win32':
        say('Linux (Proton): set the game\'s launch options to  WINEDLLOVERRIDES="winmm=n,b" %command%')


def uninstall(a):
    folder = os.path.abspath(a.recomp or pick('The TTT2 recomp\'s folder (with its exe and game folder)'))
    game = recomp_game(folder)
    say('restoring the game\'s title update overlay')
    say('  ' + overlay(game, 'restore'))
    record = os.path.join(folder, RECORD)
    info = json.load(open(record)) if os.path.isfile(record) else {}
    dll = os.path.join(folder, 'winmm.dll')
    if is_ours(dll):
        os.remove(dll)
        if info.get('winmm_backup') and os.path.isfile(info['winmm_backup']):
            os.replace(info['winmm_backup'], dll)
            say('the earlier winmm.dll is back')
    for name in (INI, RECORD, 'ttt2rick.log'):
        if os.path.isfile(os.path.join(folder, name)):
            os.remove(os.path.join(folder, name))
    say('Rick is uninstalled (the converted files stay in %s; delete that folder to free the space).' % WORK)


def main():
    ap = argparse.ArgumentParser(description='Install Rick Taylor (Splatterhouse 2010) into a TTT2 recomp.',
                                 epilog='Change jennifer / blood later in ttt2rick.ini next to the game\'s exe.')
    ap.add_argument('--recomp', help='the recomp\'s folder (its exe and game folder)')
    ap.add_argument('--iso', help='your Splatterhouse (Xbox 360, USA) disc image')
    ap.add_argument('--jennifer', dest='jennifer', action='store_true', default=None, help='Jennifer too (default)')
    ap.add_argument('--no-jennifer', dest='jennifer', action='store_false', help='Rick only')
    ap.add_argument('--blood', dest='blood', action='store_true', default=None, help='keep Splatterhouse\'s blood')
    ap.add_argument('--no-blood', dest='blood', action='store_false', help='clean (default)')
    ap.add_argument('--yes', action='store_true', help='no questions: the defaults for what is not given')
    ap.add_argument('--uninstall', action='store_true', help='take the mod out of the recomp')
    a = ap.parse_args()
    if sys.version_info < (3, 9):
        raise SystemExit('Python 3.9 or newer is needed')
    try:
        import numpy  # noqa: F401
        import PIL  # noqa: F401
    except ImportError:
        raise SystemExit('numpy and Pillow are needed: %s -m pip install -r requirements.txt' % sys.executable)
    sys.path.insert(0, ROOT)
    (uninstall if a.uninstall else install)(a)


if __name__ == '__main__':
    main()
