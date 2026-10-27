"""The TTT2 Rick Taylor mod as one zip for players: the installer, its loader DLL and the converters, no game data.

python3 mod/package.py [out.zip]          (default dist/TTT2-RickTaylor-mod.zip; build the DLL first: mod/loader/build.sh)

In it: install.py, README.txt, requirements.txt, winmm.dll (mod/loader/build), the converters (ttt2rick/, ttt2jen/,
Petexy's tag system: third_party/petexy-ttt2, as ttt2rick.convert.attacks finds it), the fighters' pictures
(work/art: the portraits and costume panels are made from them) and licenses/.
"""
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PETEXY = 'third_party/petexy-ttt2'
PETEXY_FILES = ['tools/characters/ttt2char/__init__.py', 'tools/characters/ttt2char/movesets.py',
                'tools/characters/ttt2char/convert/__init__.py', 'tools/characters/ttt2char/convert/idmaps.py',
                'tools/characters/ttt2char/convert/tagsystem.py']
ART = ['rick_taylor.png', 'jennifer_willis.png', 'mirror_rick_panel.png']
LICENSES = {'licenses/petexy-ttt2.txt': PETEXY + '/LICENSE', 'licenses/minhook.txt': 'mod/loader/minhook/LICENSE.txt',
            'licenses/XenonRecomp.md': 'mod/loader/include/XenonRecomp-LICENSE.md'}


def package_files():
    """(path in the zip, path on disk)"""
    files = [('install.py', 'mod/install.py'), ('README.txt', 'mod/README.md'),
             ('requirements.txt', 'mod/requirements.txt'), ('winmm.dll', 'mod/loader/build/winmm.dll')]
    for pkg in ('ttt2rick', 'ttt2jen'):
        for folder, dirs, names in os.walk(os.path.join(ROOT, pkg)):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for n in names:
                if n.endswith('.py') or n == 'LICENSE':
                    rel = os.path.relpath(os.path.join(folder, n), ROOT).replace(os.sep, '/')
                    files.append((rel, rel))
    files += [(PETEXY + '/' + f, PETEXY + '/' + f) for f in PETEXY_FILES]
    files += [('work/art/' + a, 'work/art/' + a) for a in ART]
    files += list(LICENSES.items())
    return files


def main(out=None):
    out = out or os.path.join(ROOT, 'dist', 'TTT2-RickTaylor-mod.zip')
    files = package_files()
    missing = [disk for _, disk in files if not os.path.isfile(os.path.join(ROOT, disk))]
    if missing:
        sys.exit('missing: %s' % ', '.join(missing))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, disk in files:
            z.write(os.path.join(ROOT, disk), 'TTT2-RickTaylor/' + name)
    print('%s: %d files, %d KB' % (out, len(files), os.path.getsize(out) // 1024))


if __name__ == '__main__':
    main(*sys.argv[1:])
