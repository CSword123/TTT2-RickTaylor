#!/bin/sh
# Build TTT2-Recomp's game exe (tekken_recomp.exe, Windows x64) on Linux, for running under Proton.
#
#   recomp/linux/build.sh <TTT2-Recomp checkout> <xwin sysroot> [jobs]
#
# Needs: clang-cl / llvm-lib / llvm-rc / llvm-mt (LLVM 21), lld-link (package lld-21), cmake, ninja, python3, and
# a Windows SDK + MSVC CRT from `xwin --accept-license splat --use-winsysroot-style` (Microsoft's license terms).
# The checkout must already hold, as its BUILDING.md describes: re/Default.xex, re/extracted_tu/<TU3>/Default.xexp,
# re/decrypted/Default_patched_tu3.bin (the installer's game/tekken.img), tools/XenonRecomp (ddd128b + the patch),
# tools/ffmpeg_dl/FFmpeg-n7.1. Steam, SDL3 and Discord are left out (optional upstream too).
set -eu
SRC=$(realpath "$1")
XWIN=$(realpath "$2")
export XWIN_SYSROOT="$XWIN"
JOBS=${3:-8}
HERE=$(dirname "$(realpath "$0")")
LLVM=/usr/lib/llvm-21/bin

# 1. the recompiled C++ (re/ppc), the runtime's patches to it, and the kernel stubs (XenonRecomp built natively)
X="$SRC/tools/XenonRecomp"
if [ ! -x "$X/build/XenonRecomp/XenonRecomp" ]; then
    cmake -S "$X" -B "$X/build" -G Ninja -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release
    cmake --build "$X/build"
fi
if [ ! -f "$SRC/re/ppc/ppc_func_mapping.cpp" ]; then
    mkdir -p "$SRC/re/ppc"                          # (XenonRecomp crashes when it is missing)
    "$X/build/XenonRecomp/XenonRecomp" "$SRC/re/recomp/tekken.toml" "$X/XenonUtils/ppc_context.h"
    python3 "$SRC/port/tools/debug_probes.py"
fi
(cd "$SRC/port/tools" && python3 check_recomp_acceptance.py)
# gen_kernel_stubs.py has its author's Windows paths: run it on this checkout's
python3 - "$SRC" <<'EOF'
import re, sys
src = sys.argv[1]
code = open(src + '/port/tools/gen_kernel_stubs.py').read()
code = re.sub(r'r"D:\\Projects\\Tekken Tag Tournament 2 \(USA, Europe\)\\([^"]*)"',
              lambda m: repr(src + '/' + m.group(1).replace('\\', '/')), code)
exec(compile(code, 'gen_kernel_stubs.py', 'exec'))
EOF

# 2. FFmpeg n7.1 configured for the XMA-only static library (the options port/third_party/ffmpeg_xma lists)
FF="$SRC/tools/ffmpeg_dl"
if [ ! -f "$FF/build/config.h" ]; then
    mkdir -p "$FF/build"
    (cd "$FF/build" && PATH="$LLVM:$PATH" "$FF/FFmpeg-n7.1/configure" --toolchain=msvc --enable-cross-compile \
        --target-os=win64 --arch=x86_64 --cc=clang-cl --cxx=clang-cl --ld=lld-link --ar=llvm-lib --nm=llvm-nm \
        --extra-cflags="/winsysroot $XWIN --target=x86_64-pc-windows-msvc" --extra-ldflags="/winsysroot:$XWIN" \
        --disable-everything --disable-programs --disable-doc --disable-avdevice --disable-avformat \
        --disable-swresample --disable-swscale --disable-postproc --disable-avfilter --disable-network --disable-asm \
        --disable-debug --disable-inline-asm --disable-autodetect --enable-decoder=wmapro,xma1,xma2 --enable-parser=xma)
fi

# 3. the game exe, with this project's runtime code (recomp/runtime/*.cpp) in the folder CMake globs
cp "$HERE/../runtime/"*.cpp "$HERE/../runtime/"*.h "$SRC/port/src/runtime/kernel/"
B="$SRC/port/build-linux"
cmake -S "$SRC/port" -B "$B" -G Ninja --toolchain "$HERE/clang-cl-xwin.cmake" -DXWIN_SYSROOT="$XWIN" \
    -DCMAKE_BUILD_TYPE= -DTTT2_PPC_OPT_LEVEL=1 -DTTT2_LOCAL_SAVES=ON -DFFMPEG_SRC="$FF/FFmpeg-n7.1" -DFFMPEG_BUILD="$FF/build"
cmake --build "$B" --target tekken_recomp --parallel "$JOBS"
ls -l "$B/tekken_recomp.exe"
