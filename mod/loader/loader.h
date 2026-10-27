// The mod's loader DLL (winmm.dll): what its generated sources (gen.py) and loader.cpp share.
#pragma once
#include "ppc_recomp_shared.h"
#include <cstddef>
#include <cstdint>

// A guest function Rick's hooks define or call: its guest address, the hook (nullptr: only called), and where its
// host code goes (for a hook, the original: MinHook's trampoline)
struct GuestFn
{
    uint32_t guest;
    PPCFunc* hook;
    PPCFunc** fn;
};
extern const GuestFn kGuestFns[];
extern const size_t kGuestFnCount;

// guest memory's host address, as the hooks are given it (set by each hook's entry)
extern uint8_t* g_guestBase;

// winmm's exports (gen.py): ordinal, name (nullptr: by ordinal only)
struct WinmmExport
{
    int ordinal;
    const char* name;
};
extern const WinmmExport kWinmmExports[];
extern const size_t kWinmmExportCount;
extern "C" void* g_winmm[];
