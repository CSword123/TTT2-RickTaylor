// Rick Taylor's roster slot (TTT2-RickTaylor project). Stage 1: TTT2_ROSTER_TRACE=1 logs the character tables'
// accessors (argument, result, caller), each distinct (function, argument, caller) once, to map the select screen.
#include "kernel_shared.h"
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <set>
#include <string>
#include <tuple>

extern "C" PPC_FUNC(__imp__sub_822763B0);
extern "C" PPC_FUNC(__imp__sub_82276158);
extern "C" PPC_FUNC(__imp__sub_82288018);

namespace {
bool Trace()
{
    static const bool on = [] { const char* e = std::getenv("TTT2_ROSTER_TRACE"); return e && (*e == '1' || *e == '2'); }();
    return on;
}

void Log(const char* fn, uint32_t arg, uint32_t lr, uint32_t result)
{
    static std::mutex m;
    static std::set<std::tuple<const char*, uint32_t, uint32_t>> seen;
    std::lock_guard l(m);
    if (seen.size() > 20000 || !seen.emplace(fn, arg, lr).second) return;
    std::fprintf(stderr, "[roster] %s(%d) = %08X  lr=%08X\n", fn, int(arg), result, lr);
}
} // namespace

#define ROSTER_TRACE(addr, label)                                              \
    PPC_FUNC(sub_##addr)                                                       \
    {                                                                          \
        const uint32_t arg = ctx.r3.u32, lr = uint32_t(ctx.lr);                \
        __imp__sub_##addr(ctx, base);                                          \
        if (Trace()) Log(label, arg, lr, ctx.r3.u32);                          \
    }

ROSTER_TRACE(822763B0, "select_to_record")  // +8 value -> record index
ROSTER_TRACE(82276158, "id_to_code")        // internal id -> code string

PPC_FUNC(sub_82288018)                      // (this, ?, select id): a name built from the select-id string table
{
    const uint32_t arg = ctx.r5.u32, lr = uint32_t(ctx.lr);
    __imp__sub_82288018(ctx, base);
    if (Trace()) Log("select_name", arg, lr, ctx.r3.u32);
}

extern "C" PPC_FUNC(__imp__sub_8227AE48);
PPC_FUNC(sub_8227AE48)                      // (player) -> internal id of the fighter it shows
{
    const uint32_t player = ctx.r3.u32, lr = uint32_t(ctx.lr);
    const uint32_t sel = GRead32(base, player + 56), table = GRead32(base, player + 33272);
    __imp__sub_8227AE48(ctx, base);
    if (Trace())
    {
        static std::mutex m;
        static std::set<std::tuple<uint32_t, uint32_t, uint32_t>> seen;
        std::lock_guard l(m);
        if (seen.size() < 5000 && seen.emplace(player, sel, lr).second)
            std::fprintf(stderr, "[roster] player %08X +56=%d table=%08X -> id %d  lr=%08X\n", player, int(sel), table,
                         int(ctx.r3.u32), lr);
    }
}

// TTT2_ROSTER_TRACE=2 also logs the strings the two CRC-32 functions hash (each distinct string once).
static void LogCrc(const char* fn, uint8_t* base, uint32_t p, uint32_t n, uint32_t lr, uint32_t result)
{
    static const bool on = [] { const char* e = std::getenv("TTT2_ROSTER_TRACE"); return e && *e == '2'; }();
    if (!on || p < 0x1000) return;
    static std::atomic<int> raw{ 0 };
    if (raw++ < 60)
    {
        char hex[100] = {};
        for (uint32_t i = 0; i < n && i < 32; ++i) std::snprintf(hex + 2 * i, 3, "%02X", base[p + i]);
        std::fprintf(stderr, "[crc-raw] %s len %u %s = %08X lr=%08X\n", fn, n, hex, result, lr);
    }
    if (n == 0 || n > 96) return;
    std::string s(reinterpret_cast<const char*>(base + p), n);
    for (char c : s) if (c < 32 || c > 126) return;
    static std::mutex m;
    static std::set<std::string> seen;
    std::lock_guard l(m);
    if (seen.size() < 20000 && seen.insert(s).second)
        std::fprintf(stderr, "[crc] %s '%s' = %08X lr=%08X\n", fn, s.c_str(), result, lr);
}

extern "C" PPC_FUNC(__imp__sub_82381C80);
extern "C" PPC_FUNC(__imp__sub_826DA208);
PPC_FUNC(sub_82381C80)
{
    const uint32_t p = ctx.r3.u32, n = ctx.r4.u32, lr = uint32_t(ctx.lr);
    __imp__sub_82381C80(ctx, base);
    LogCrc("crcA", base, p, n, lr, ctx.r3.u32);
}
PPC_FUNC(sub_826DA208)
{
    const uint32_t p = ctx.r3.u32, n = ctx.r4.u32, lr = uint32_t(ctx.lr);
    __imp__sub_826DA208(ctx, base);
    LogCrc("crcB", base, p, n, lr, ctx.r3.u32);
}
extern "C" PPC_FUNC(__imp__sub_82D2E228);
PPC_FUNC(sub_82D2E228)                      // zlib's crc32(crc, buf, len)
{
    const uint32_t p = ctx.r4.u32, n = ctx.r5.u32, lr = uint32_t(ctx.lr);
    __imp__sub_82D2E228(ctx, base);
    LogCrc("crc32", base, p, n, lr, ctx.r3.u32);
}
