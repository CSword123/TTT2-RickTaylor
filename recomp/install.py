"""Apply this project's patches to a checkout of thatcalikid760/TTT2-Recomp.

python3 recomp/install.py <TTT2-Recomp checkout> [--check]

The patches are made against PINNED; another commit is refused unless --force, since the
recompiled game functions they will hook (sub_XXXXXXXX) are tied to the exact build. Patches
already applied are skipped, so the script can run again after a pull.
"""
import argparse
import os
import subprocess
import sys

PINNED = 'ca18211'
HERE = os.path.dirname(os.path.abspath(__file__))
PATCHES = os.path.join(HERE, 'patches')


def git(checkout, *args):
    return subprocess.run(['git', '-C', checkout, *args], capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('checkout')
    ap.add_argument('--check', action='store_true', help='only report what would be applied')
    ap.add_argument('--force', action='store_true', help='patch a commit other than %s' % PINNED)
    args = ap.parse_args()

    head = git(args.checkout, 'rev-parse', '--short=7', 'HEAD')
    if head.returncode:
        sys.exit('not a git checkout: %s' % args.checkout)
    head = head.stdout.strip()
    if head != PINNED and not args.force:
        sys.exit('checkout is at %s, the patches are for %s (--force to try anyway)' % (head, PINNED))

    for name in sorted(os.listdir(PATCHES)):
        patch = os.path.join(PATCHES, name)
        if not git(args.checkout, 'apply', '--reverse', '--check', patch).returncode:
            print('%s: already applied' % name)
            continue
        r = git(args.checkout, 'apply', '--check', patch)
        if r.returncode:
            sys.exit('%s: does not apply\n%s' % (name, r.stderr))
        if args.check:
            print('%s: would apply' % name)
            continue
        r = git(args.checkout, 'apply', patch)
        if r.returncode:
            sys.exit('%s: failed\n%s' % (name, r.stderr))
        print('%s: applied' % name)


if __name__ == '__main__':
    main()
