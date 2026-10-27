#!/bin/sh
# Build the mod's loader, winmm.dll (Windows x64), on Linux with LLVM's MSVC-compatible tools and an xwin sysroot
# (as recomp/linux/build.sh: clang-cl / lld-link 21, `xwin --accept-license splat --use-winsysroot-style`).
#
#   mod/loader/build.sh <xwin sysroot> [out folder: mod/loader/build]
#
# Compiles Rick's hooks (recomp/runtime/rick_slot.cpp, rick_voice.cpp) against mod/loader/include, the stand-ins for
# the recomp's headers, with the sources gen.py makes from them, loader.cpp and MinHook (mod/loader/minhook).
set -eu
HERE=$(dirname "$(realpath "$0")")
ROOT=$(realpath "$HERE/../..")
XWIN=$(realpath "$1")
OUT=$(realpath -m "${2:-$HERE/build}")
LLVM=/usr/lib/llvm-21/bin
mkdir -p "$OUT/obj"
HOOKS="$ROOT/recomp/runtime/rick_slot.cpp $ROOT/recomp/runtime/rick_voice.cpp"
SYS="/winsysroot $XWIN --target=x86_64-pc-windows-msvc"
INC="-I$OUT -I$HERE -I$HERE/include -I$ROOT/recomp/runtime -I$HERE/minhook/include"
CXX="$LLVM/clang-cl $SYS /nologo /std:c++20 /EHsc /O2 /MT /clang:-march=x86-64-v2 -Wno-unused-function -D_CRT_SECURE_NO_WARNINGS -DTTT2RICK_MOD=1 $INC"

# 1. the hooks' guest functions and winmm's exports (gen.py reads the hooks preprocessed)
for f in $HOOKS; do
    $CXX -DTTT2RICK_GEN_PASS /E "$f" > "$OUT/obj/$(basename "$f" .cpp).i"
done
python3 "$HERE/gen.py" "$OUT" "$HERE/winmm_exports.txt" "$OUT"/obj/*.i

# 2. compile and link
OBJS=""
for f in $HOOKS "$HERE/loader.cpp" "$OUT/guest_fns.gen.cpp" "$OUT/winmm.gen.cpp"; do
    o="$OUT/obj/$(basename "$f" .cpp).obj"
    $CXX /c "$f" /Fo"$o"
    OBJS="$OBJS $o"
done
for f in "$HERE"/minhook/src/buffer.c "$HERE"/minhook/src/hook.c "$HERE"/minhook/src/trampoline.c \
         "$HERE"/minhook/src/hde/hde64.c; do
    o="$OUT/obj/mh_$(basename "$f" .c).obj"
    $LLVM/clang-cl $SYS /nologo /O2 /MT -I"$HERE/minhook/include" /c "$f" /Fo"$o"
    OBJS="$OBJS $o"
done
$LLVM/lld-link /nologo /dll /winsysroot:"$XWIN" /machine:x64 /def:"$OUT/winmm.def" /out:"$OUT/winmm.dll" \
    $OBJS kernel32.lib user32.lib
ls -l "$OUT/winmm.dll"
