// Rick Taylor's roster slot (TTT2-RickTaylor project). Stage 1: TTT2_ROSTER_TRACE=1 logs the character tables'
// accessors (argument, result, caller), each distinct (function, argument, caller) once, to map the select screen.
#include "kernel_shared.h"
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <set>
#include <tuple>

extern "C" PPC_FUNC(__imp__sub_822761A0);
extern "C" PPC_FUNC(__imp__sub_82276270);
extern "C" PPC_FUNC(__imp__sub_822762A8);
extern "C" PPC_FUNC(__imp__sub_822762E0);
extern "C" PPC_FUNC(__imp__sub_82276310);
extern "C" PPC_FUNC(__imp__sub_82276348);
extern "C" PPC_FUNC(__imp__sub_82276380);
extern "C" PPC_FUNC(__imp__sub_822763B0);
extern "C" PPC_FUNC(__imp__sub_82276408);
extern "C" PPC_FUNC(__imp__sub_82276158);
extern "C" PPC_FUNC(__imp__sub_82288018);

namespace {
bool Trace()
{
    static const bool on = [] { const char* e = std::getenv("TTT2_ROSTER_TRACE"); return e && *e == '1'; }();
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

ROSTER_TRACE(822761A0, "record")            // record index -> record address
ROSTER_TRACE(82276270, "record_call")       // calls the record's +20 function
ROSTER_TRACE(822762A8, "record_slot")       // +4
ROSTER_TRACE(822762E0, "record_id")         // +0 internal id
ROSTER_TRACE(82276310, "record_place")      // +12
ROSTER_TRACE(82276348, "id_to_select")      // internal id -> +8 of its first record
ROSTER_TRACE(82276380, "record_select")     // +8
ROSTER_TRACE(822763B0, "select_to_record")  // +8 value -> record index
ROSTER_TRACE(82276408, "record_enabled")    // +80
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
