"""Generated sources of the mod's loader DLL (winmm.dll): Rick's hooks, compiled outside the recomp, and the winmm
exports it forwards to the system's winmm.

python3 mod/loader/gen.py <out folder> <winmm_exports.txt> <preprocessed hook source> ...

From the hook sources (recomp/runtime/*.cpp, preprocessed with mod/loader/include ahead of the recomp's headers):
every guest function they define is a hook (`void sub_XXXXXXXX(PPCContext& ...) {`), and every other one they
name is a guest function they call. guest_fns.gen.h declares them all (the stand-in ppc_recomp_shared.h includes
it); guest_fns.gen.cpp defines, per guest function, the host code the loader finds for it (loader.cpp: a hook's
original, MinHook's trampoline, as __imp__sub_X; another's as sub_X and __imp__sub_X) and kGuestFns, the table the
loader fills and hooks from.

From winmm_exports.txt (ordinal and name per line, a lone ordinal for an export without a name: Wine's winmm.dll,
the same set as Windows'): winmm.gen.cpp, a stub per export that jumps to the system winmm's own (g_winmm, filled by
loader.cpp), and winmm.def, which exports the stubs under the same names and ordinals.
"""
import os
import re
import sys

DEFINED = re.compile(r'\bvoid\s+sub_([0-9A-F]{8})\s*\(\s*PPCContext\s*&\s*__restrict\s+ctx\s*,\s*uint8_t\s*\*\s*base\s*\)'
                     r'\s*\{')
NAMED = re.compile(r'\b(?:__imp__)?sub_([0-9A-F]{8})\b')


def guest_functions(sources):
    hooks, named = set(), set()
    for path in sources:
        text = open(path, encoding='latin-1').read()
        hooks.update(DEFINED.findall(text))
        named.update(NAMED.findall(text))
    return sorted(hooks), sorted(named)


def write_guest(out, hooks, named):
    with open(os.path.join(out, 'guest_fns.gen.h'), 'w') as f:
        f.write('// mod/loader/gen.py: the guest functions Rick\'s hooks define or call\n#pragma once\n')
        for a in named:
            f.write('PPC_EXTERN_FUNC(sub_%s);\nextern "C" PPC_FUNC(__imp__sub_%s);\n' % (a, a))
    with open(os.path.join(out, 'guest_fns.gen.cpp'), 'w') as f:
        f.write('// mod/loader/gen.py: host code for the guest functions Rick\'s hooks define or call\n'
                '#include "ppc_recomp_shared.h"\n#include "loader.h"\n\nnamespace {\nPPCFunc* g_fn[%d];\n}\n\n'
                % len(named))
        for i, a in enumerate(named):
            if a in hooks:          # the hook is sub_X (the hook sources); the original, the trampoline
                f.write('extern "C" PPC_FUNC(__imp__sub_%s) { g_fn[%d](ctx, base); }\n'
                        'static PPC_FUNC(hook_%s) { g_guestBase = base; sub_%s(ctx, base); }\n' % (a, i, a, a))
            else:
                f.write('PPC_FUNC(sub_%s) { g_fn[%d](ctx, base); }\n'
                        'extern "C" PPC_FUNC(__imp__sub_%s) { g_fn[%d](ctx, base); }\n' % (a, i, a, i))
        f.write('\nconst GuestFn kGuestFns[] = {\n')
        for i, a in enumerate(named):
            f.write('    { 0x%s, %s, &g_fn[%d] },\n' % (a, 'hook_' + a if a in hooks else 'nullptr', i))
        f.write('};\nconst size_t kGuestFnCount = %d;\n' % len(named))


def write_winmm(out, exports_txt):
    exports = []
    for line in open(exports_txt):
        parts = line.split()
        if parts:
            exports.append((int(parts[0]), parts[1] if len(parts) > 1 else None))
    with open(os.path.join(out, 'winmm.gen.cpp'), 'w') as f:
        f.write('// mod/loader/gen.py: winmm\'s exports, each a jump to the system winmm\'s own (g_winmm)\n'
                '#include "loader.h"\n\nextern "C" void* g_winmm[%d];\nvoid* g_winmm[%d];\n'
                'const WinmmExport kWinmmExports[] = {\n' % (len(exports), len(exports)))
        for ordinal, name in exports:
            f.write('    { %d, %s },\n' % (ordinal, '"%s"' % name if name else 'nullptr'))
        f.write('};\nconst size_t kWinmmExportCount = %d;\n\n' % len(exports))
        for i, _ in enumerate(exports):
            f.write('extern "C" __attribute__((naked)) void winmm_stub_%d() { __asm__("jmpq *g_winmm+%d(%%rip)"); }\n'
                    % (i, 8 * i))
    with open(os.path.join(out, 'winmm.def'), 'w') as f:
        f.write('LIBRARY winmm\nEXPORTS\n')
        for i, (ordinal, name) in enumerate(exports):
            if name:
                f.write('    %s=winmm_stub_%d @%d\n' % (name, i, ordinal))
            else:
                f.write('    winmm_ordinal_%d=winmm_stub_%d @%d NONAME\n' % (ordinal, i, ordinal))


def main(out, exports_txt, *sources):
    os.makedirs(out, exist_ok=True)
    hooks, named = guest_functions(sources)
    write_guest(out, hooks, named)
    write_winmm(out, exports_txt)
    print('%d guest functions (%d hooked), winmm exports from %s' % (len(named), len(hooks), exports_txt))


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
