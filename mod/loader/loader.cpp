// The TTT2 Rick Taylor mod's loader: winmm.dll next to a Tekken Tag Tournament 2 recomp's exe (thatcalikid760's
// TTT2-Recomp, or shihabal3amri's port it is a fork of: both XenonRecomp builds of the same Default.xex + Title
// Update 3, so their guest functions are at the same guest addresses).
//
// The exe imports winmm (timeBeginPeriod), so Windows loads this DLL from the exe's folder before the game starts
// (under Proton/Wine: WINEDLLOVERRIDES="winmm=n,b"). It
// - forwards every winmm export to the system's winmm (winmm.gen.cpp, mod/loader/gen.py);
// - finds the recomp's PPCFuncMappings, the {guest address, host function} table every XenonRecomp build carries
//   (its runtime fills the indirect-call table from it), by scanning the exe's data for it;
// - hooks, with MinHook, the host function of each guest function Rick's hooks (recomp/runtime/rick_*.cpp, compiled
//   into this DLL) replace. Every recompiled function is a weak, noinline sub_X alias of __imp__sub_X: callers reach
//   it through that one address, never inlined, so a detour there takes every call, as the hooks' strong
//   definitions do when they are built into the recomp itself. A hook's __imp__sub_X is MinHook's trampoline.
// Nothing is hooked when ttt2rick.ini (or TTT2_RICK=0) turns the mod off, when any guest function is missing, or
// when the exe was built with Rick's hooks in it already (recomp/linux/build.sh: they would run twice).
// It logs to ttt2rick.log next to the exe.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "loader.h"
#include "rick_settings.h"
#include "MinHook.h"
#include <cstdarg>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <string>
#include <unordered_map>

uint8_t* g_guestBase = nullptr;

namespace {
constexpr uint32_t kGuestLow = 0x82000000, kGuestHigh = 0x84000000;
constexpr uint32_t kExAllocatePool = 0x82DB818C;     // the game's import thunk of the kernel's ExAllocatePool
constexpr size_t kMinMappings = 10000;               // the TU3 image has about 80000 functions

PPCFunc* g_exAllocatePool = nullptr;
FILE* g_log = nullptr;

void Log(const char* fmt, ...)
{
    va_list a;
    va_start(a, fmt);
    char line[1024];
    std::vsnprintf(line, sizeof(line), fmt, a);
    va_end(a);
    std::fprintf(stderr, "[ttt2rick] %s\n", line);
    if (g_log) { std::fprintf(g_log, "%s\n", line); std::fflush(g_log); }
}

std::string ExeFolder()
{
    char exe[MAX_PATH] = {};
    GetModuleFileNameA(nullptr, exe, MAX_PATH);
    std::string path(exe);
    return path.substr(0, path.find_last_of("\\/") + 1);
}

extern "C" uint32_t MissingWinmmExport() { return 0; }

// the system's winmm, for the forwarded exports
bool ForwardWinmm(HMODULE self)
{
    wchar_t path[MAX_PATH] = {};
    GetSystemDirectoryW(path, MAX_PATH);
    wcscat_s(path, L"\\winmm.dll");
    HMODULE real = LoadLibraryW(path);
    if (!real || real == self)
    {
        Log("cannot load the system's winmm.dll (%p)", (void*)real);
        for (size_t i = 0; i < kWinmmExportCount; ++i) g_winmm[i] = (void*)&MissingWinmmExport;
        return false;
    }
    size_t missing = 0;
    for (size_t i = 0; i < kWinmmExportCount; ++i)
    {
        const WinmmExport& e = kWinmmExports[i];
        FARPROC p = GetProcAddress(real, e.name ? e.name : MAKEINTRESOURCEA(e.ordinal));
        g_winmm[i] = p ? (void*)p : (void*)&MissingWinmmExport;
        missing += !p;
    }
    if (missing) Log("winmm: %zu of %zu exports missing in the system's (they return 0)", missing, kWinmmExportCount);
    return true;
}

// PPCFuncMappings: the longest run, in the exe's initialized data, of {u64 guest address, host function in the
// exe} pairs
std::unordered_map<uint32_t, PPCFunc*> FindMappings()
{
    std::unordered_map<uint32_t, PPCFunc*> map;
    auto* image = reinterpret_cast<uint8_t*>(GetModuleHandleW(nullptr));
    auto* nt = reinterpret_cast<IMAGE_NT_HEADERS64*>(image + reinterpret_cast<IMAGE_DOS_HEADER*>(image)->e_lfanew);
    const uintptr_t lo = uintptr_t(image), hi = lo + nt->OptionalHeader.SizeOfImage;
    const uint64_t* best = nullptr;
    size_t bestLength = 0;
    IMAGE_SECTION_HEADER* section = IMAGE_FIRST_SECTION(nt);
    for (unsigned s = 0; s < nt->FileHeader.NumberOfSections; ++s, ++section)
    {
        if (!(section->Characteristics & IMAGE_SCN_CNT_INITIALIZED_DATA) ||
            (section->Characteristics & IMAGE_SCN_MEM_EXECUTE))
            continue;
        const auto* words = reinterpret_cast<const uint64_t*>(image + section->VirtualAddress);
        const size_t count = std::min<size_t>(section->Misc.VirtualSize, section->SizeOfRawData) / 8;
        for (size_t parity = 0; parity < 2; ++parity)
        {
            size_t start = parity, length = 0;
            for (size_t i = parity; i + 1 < count; i += 2)
            {
                const uint64_t guest = words[i], host = words[i + 1];
                const bool entry = guest >= kGuestLow && guest < kGuestHigh && (guest & 3) == 0 && host >= lo &&
                                   host < hi;
                if (entry)
                {
                    if (!length) start = i;
                    if (++length > bestLength) { bestLength = length; best = words + start; }
                }
                else
                    length = 0;
            }
        }
    }
    if (bestLength < kMinMappings)
    {
        Log("no PPCFuncMappings table in the exe (longest run %zu): not a TTT2 XenonRecomp build?", bestLength);
        return map;
    }
    for (size_t i = 0; i < bestLength; ++i)
        map.emplace(uint32_t(best[2 * i]), reinterpret_cast<PPCFunc*>(best[2 * i + 1]));
    Log("PPCFuncMappings: %zu functions at %p", bestLength, (const void*)best);
    return map;
}

// the exe has Rick's hooks built in: a string of theirs is in its image (they read the variable TTT2_RICK_BLOOD)
bool BuiltIn()
{
    auto* image = reinterpret_cast<const uint8_t*>(GetModuleHandleW(nullptr));
    auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(image + reinterpret_cast<const IMAGE_DOS_HEADER*>(image)->e_lfanew);
    static const char mark[] = "TTT2_RICK_BLOOD";
    const uint8_t* end = image + nt->OptionalHeader.SizeOfImage - sizeof(mark);
    const IMAGE_SECTION_HEADER* section = IMAGE_FIRST_SECTION(nt);
    for (unsigned s = 0; s < nt->FileHeader.NumberOfSections; ++s, ++section)
    {
        if (section->Characteristics & (IMAGE_SCN_MEM_EXECUTE | IMAGE_SCN_CNT_UNINITIALIZED_DATA)) continue;
        const uint8_t* p = image + section->VirtualAddress;
        const uint8_t* stop = std::min(end, p + std::min<size_t>(section->Misc.VirtualSize, section->SizeOfRawData));
        for (; p < stop; ++p)
            if (*p == 'T' && std::memcmp(p, mark, sizeof(mark)) == 0) return true;
    }
    return false;
}

bool InstallHooks()
{
    if (BuiltIn())
    {
        Log("this exe has Rick's hooks built in: the loader stays out");
        return false;
    }
    const auto map = FindMappings();
    if (map.empty()) return false;
    auto at = [&](uint32_t guest) { const auto it = map.find(guest); return it == map.end() ? nullptr : it->second; };
    size_t missing = 0;
    for (size_t i = 0; i < kGuestFnCount; ++i)
        if (!at(kGuestFns[i].guest)) { Log("guest function %08X not in the exe", kGuestFns[i].guest); ++missing; }
    g_exAllocatePool = at(kExAllocatePool);
    if (!g_exAllocatePool) { Log("ExAllocatePool's thunk %08X not in the exe", kExAllocatePool); ++missing; }
    if (missing)
    {
        Log("%zu guest functions missing: Rick is not loaded (a recomp of another game image?)", missing);
        return false;
    }
    // host functions several guest functions share (identical code folded by the linker): a hook there runs for all
    // of them (its hooks pass what is not theirs on to the original)
    std::unordered_map<PPCFunc*, int> shared;
    for (const auto& [guest, host] : map) ++shared[host];
    if (MH_Initialize() != MH_OK) { Log("MinHook did not start"); return false; }
    size_t hooks = 0;
    for (size_t i = 0; i < kGuestFnCount; ++i)
    {
        const GuestFn& f = kGuestFns[i];
        PPCFunc* host = at(f.guest);
        if (!f.hook) { *f.fn = host; continue; }
        if (shared[host] > 1) Log("sub_%08X shares its host code with %d other functions", f.guest, shared[host] - 1);
        const MH_STATUS st = MH_CreateHook(reinterpret_cast<void*>(host), reinterpret_cast<void*>(f.hook),
                                           reinterpret_cast<void**>(f.fn));
        if (st != MH_OK)
        {
            Log("cannot hook sub_%08X (%s): Rick is not loaded", f.guest, MH_StatusToString(st));
            MH_RemoveHook(MH_ALL_HOOKS);
            MH_Uninitialize();
            return false;
        }
        ++hooks;
    }
    if (MH_EnableHook(MH_ALL_HOOKS) != MH_OK) { Log("cannot enable the hooks"); return false; }
    Log("%zu hooks on, %zu guest functions called", hooks, kGuestFnCount - hooks);
    return true;
}
}   // namespace

// g_virtualHeap.Alloc's stand-in (guest_heap.h): `size` bytes of guest memory from the game's ExAllocatePool, aligned
void* ModGuestAlloc(size_t size, size_t align)
{
    if (!g_exAllocatePool || !g_guestBase) return nullptr;
    PPCContext ctx{};
    ctx.r3.u64 = uint32_t(size + align);
    g_exAllocatePool(ctx, g_guestBase);
    if (!ctx.r3.u32) return nullptr;
    const uintptr_t p = uintptr_t(g_guestBase + ctx.r3.u32);
    return reinterpret_cast<void*>((p + align - 1) & ~uintptr_t(align - 1));
}

BOOL WINAPI DllMain(HINSTANCE self, DWORD reason, LPVOID)
{
    if (reason != DLL_PROCESS_ATTACH) return TRUE;
    DisableThreadLibraryCalls(self);
    g_log = std::fopen((ExeFolder() + "ttt2rick.log").c_str(), "w");
    ForwardWinmm(self);
    if (!RickSetting("TTT2_RICK", kRickByDefault))
    {
        Log("off (ttt2rick.ini rick = 0, or TTT2_RICK=0): the game is unchanged");
        return TRUE;
    }
    Log("Rick %s, Jennifer %s, blood %s", "on", RickSetting("TTT2_JEN", true) ? "on" : "off",
        RickSetting("TTT2_RICK_BLOOD", false) ? "on" : "off");
    InstallHooks();
    return TRUE;
}
