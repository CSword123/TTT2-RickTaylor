// Rick Taylor as an added fighter of his own (TTT2-RickTaylor project; design after Petexy's Wii U port, whose
// runtime/src/title/roster.cpp does this for its character packs). TTT2_RICK=1 turns it on.
//
// Rick is internal id 64 (the title's ids end at 62; 63 means random/none), records 140 and 141 (copies of
// Marduk's, held here), motion row 58 (a row no record uses) and code "ric": his body files ric.nud/.nut/.bon/.xml
// come from the title update's overlay (ttt2rick.ttt2.overlay), his moveset is Marduk's under a key of its own.
// Addresses: recomp/ROSTER.md.
#include "kernel_shared.h"
#include "guest_heap.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

extern "C" PPC_FUNC(__imp__sub_82468AD0);   // builds the chara master (r3) and the key registry
extern "C" PPC_FUNC(__imp__sub_8246A054);   // the same, for the other build
PPC_FUNC(sub_823011F8);          // chara master string: (this, char*)
PPC_FUNC(sub_8247C480);          // chara master: add(this, id, row, &name, &code)
PPC_FUNC(sub_82429C58);          // registry string: (this, char*)
PPC_FUNC(sub_82336FC0);          // its destructor
PPC_FUNC(sub_8247DDB0);          // registry: add a code (registry, &code)
PPC_FUNC(sub_8247A628);          // registry: (registry, &code, type, &key)
PPC_FUNC(sub_82472220);          // registry: (registry, &code, type, &key, index)

extern "C" PPC_FUNC(__imp__sub_822761A0);   // record(i) -> address
extern "C" PPC_FUNC(__imp__sub_82276270);   // record(i)'s +20 function
extern "C" PPC_FUNC(__imp__sub_822762A8);   // +4 costume slot
extern "C" PPC_FUNC(__imp__sub_822762E0);   // +0 internal id
extern "C" PPC_FUNC(__imp__sub_82276310);   // +12 motion row
extern "C" PPC_FUNC(__imp__sub_82276348);   // id -> +8 of its first record
extern "C" PPC_FUNC(__imp__sub_82276380);   // +8 UI place
extern "C" PPC_FUNC(__imp__sub_82276408);   // +80 enabled
extern "C" PPC_FUNC(__imp__sub_822761D0);   // id -> how many records
extern "C" PPC_FUNC(__imp__sub_82276200);   // id -> first record
extern "C" PPC_FUNC(__imp__sub_82276218);   // (id, i) -> record i
extern "C" PPC_FUNC(__imp__sub_82276440);   // motion row -> record
extern "C" PPC_FUNC(__imp__sub_82331B50);   // a player's fighter from a record: loadPlayer ... <code>

namespace {
constexpr uint32_t kId = 64, kRecord0 = 140, kRow = 58, kDonorId = 17, kDonorRecord0 = 36;
constexpr uint32_t kRecords = 0x82DC21B8, kRecordSize = 84, kTitleRecords = 139;
constexpr uint32_t kMotionRows = 0x820A24B4;            // 68 x {moveset, move list, motion pack}
constexpr uint32_t kCodes = 0x82DD1CC8;                  // 63 x char*, by internal id
constexpr uint32_t kGrids = 0x8200C8BC;                  // {cells, count} by mode
constexpr uint32_t kRegistryPtr = 0x82EE0B5C;
constexpr uint32_t kMovesetKey = 0x52494331;             // "RIC1": Marduk's moveset with Rick's id, from the overlay
constexpr uint32_t kDonorMoveList = 0x68A7CEF7, kDonorMotions = 0x75F7BE7E;

// Marduk's registry entries (sub_8244E618), replayed for "ric" with his own body files' keys.
enum class Op { Code, File, Part };
struct Reg { Op op; uint32_t type, key, index; };
constexpr Reg kDonorRegistry[] = {
    {Op::Code, 0, 0, 0},
    {Op::File, 0, 0x4F17AB5F, 0}, {Op::File, 1, 0x52A0BB3B, 0}, {Op::File, 2, 0x16F541FE, 0},
    {Op::File, 3, 0xE7A63BA0, 0}, {Op::File, 4, 0x1F57F9CE, 0},
    {Op::Code, 0, 0, 0},
    {Op::File, 6, 0xDB7C64F6, 0}, {Op::File, 7, 0x13E3AFD7, 0}, {Op::File, 8, 0x0E54BFB3, 0},
    {Op::File, 9, 0x4A014576, 0}, {Op::File, 10, 0x20390BBD, 0}, {Op::File, 11, 0xBB523F28, 0},
    {Op::File, 13, 0xDE98FCDE, 0}, {Op::File, 15, 0x0E54BFB3, 0}, {Op::File, 12, 0x4A014576, 0},
    {Op::Part, 14, 0x8C213401, 0}, {Op::Part, 14, 0xB1411DB1, 1}, {Op::Part, 14, 0xF6E16761, 2},
    {Op::Part, 14, 0xCB814ED1, 3}, {Op::Part, 14, 0x79A192C1, 4}, {Op::Part, 14, 0x44C1BB71, 5},
    {Op::Part, 14, 0x0361C1A1, 6}, {Op::Part, 14, 0x3E01E811, 7}, {Op::Part, 14, 0xBC517FC0, 8},
    {Op::Part, 14, 0x81315670, 9}, {Op::Part, 14, 0x741194A1, 10}, {Op::Part, 14, 0x4971BD11, 11},
    {Op::Part, 14, 0x0ED1C7C1, 12}, {Op::Part, 14, 0x33B1EE71, 13}, {Op::Part, 14, 0x81913261, 14},
    {Op::Part, 14, 0xBCF11BD1, 15}, {Op::Part, 14, 0xFB516101, 16}, {Op::Part, 14, 0xC63148B1, 17},
    {Op::Part, 14, 0x4461DF60, 18}, {Op::Part, 14, 0x7901F6D0, 19},
};

bool On()
{
    static const bool on = [] { const char* e = std::getenv("TTT2_RICK"); return e && *e == '1'; }();
    return on;
}

uint32_t Crc(const char* s)                              // the archives' keys: zlib.crc32(name, 0xFFFFFFFF)
{
    uint32_t c = 0;
    for (; *s; ++s)
    {
        c ^= uint8_t(*s);
        for (int k = 0; k < 8; ++k) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1)));
    }
    return ~c;
}

uint8_t* g_mem = nullptr;
uint32_t Guest(const void* p) { return uint32_t(static_cast<const uint8_t*>(p) - g_mem); }

struct State
{
    uint32_t records = 0;           // our two records
    uint32_t code = 0;              // "ric\0"
    uint32_t scratch = 0;           // string objects and keys for the guest calls
    bool ready = false, registered = false;
} g;

uint32_t Alloc(uint8_t* base, uint32_t size)
{
    void* p = g_virtualHeap.Alloc(size, 16);
    std::memset(p, 0, size);
    return uint32_t(static_cast<uint8_t*>(p) - base);
}

void Call(PPCContext& ctx, uint8_t* base, void (*fn)(PPCContext&, uint8_t*), std::initializer_list<uint32_t> args)
{
    PPCContext saved = ctx;
    PPCRegister* regs[] = { &ctx.r3, &ctx.r4, &ctx.r5, &ctx.r6, &ctx.r7, &ctx.r8 };
    uint32_t i = 0;
    for (uint32_t a : args) regs[i++]->u64 = a;
    fn(ctx, base);
    const uint64_t r3 = ctx.r3.u64;
    ctx = saved;
    ctx.r3.u64 = r3;
}

// One-time set-up: the records, the motion row and the grids.
void Prepare(uint8_t* base)
{
    if (g.ready) return;
    g.ready = true;
    g_mem = base;
    g.records = Alloc(base, 2 * kRecordSize);
    for (uint32_t k = 0; k < 2; ++k)
    {
        const uint32_t r = g.records + k * kRecordSize;
        std::memcpy(base + r, base + kRecords + (kDonorRecord0 + k) * kRecordSize, kRecordSize);
        GWrite32(base, r + 0, kId);
        GWrite32(base, r + 12, kRow);
    }
    g.code = Alloc(base, 16);
    std::memcpy(base + g.code, "ric", 4);
    g.scratch = Alloc(base, 1024);

    const uint32_t row = kMotionRows + 12 * kRow;
    GWrite32(base, row + 0, kMovesetKey);
    GWrite32(base, row + 4, kDonorMoveList);
    GWrite32(base, row + 8, kDonorMotions);

    // The full grids (modes 1 and 2: 62 cells, the top row columns 3-18) get a 63rd cell: Rick at column 19 of
    // the top row, in the row's ring (right of cell 61, left of 46) and above the middle row's column 19 (cell 19).
    for (uint32_t mode = 1; mode <= 2; ++mode)
    {
        const uint32_t entry = kGrids + 8 * mode, cells = GRead32(base, entry), count = GRead32(base, entry + 4);
        if (count != 62) continue;
        const uint32_t copy = Alloc(base, 32 * 63);
        std::memcpy(base + copy, base + cells, 32 * 62);
        const uint32_t rick = copy + 32 * 62;
        const int32_t fields[8] = { int32_t(kId), 51, 42, 19, 61, 46, 19, 0 };   // id, 51, up, down, left, right, column, row
        for (int i = 0; i < 8; ++i) GWrite32(base, rick + 4 * i, uint32_t(fields[i]));
        GWrite32(base, copy + 32 * 61 + 20, 62);    // cell 61's right
        GWrite32(base, copy + 32 * 46 + 16, 62);    // cell 46's left
        GWrite32(base, copy + 32 * 19 + 8, 62);     // the middle row's column 19: up
        GWrite32(base, copy + 32 * 42 + 12, 62);    // the bottom row's column 19: down
        GWrite32(base, entry, copy);
        GWrite32(base, entry + 4, 63);
    }
    std::fprintf(stderr, "[rick] records %08X, motion row %u, code 'ric' (id %u)\n", g.records, kRow, kId);
}

void Register(PPCContext& ctx, uint8_t* base, uint32_t master)
{
    Prepare(base);
    const uint32_t s = g.scratch;
    const uint32_t name = s, code = s + 128, text = s + 256, key = s + 288;
    // the chara master: {id, motion row, name, code}
    std::memcpy(base + text, "Rick", 5);
    Call(ctx, base, sub_823011F8, { name, text });
    Call(ctx, base, sub_823011F8, { code, g.code });
    Call(ctx, base, sub_8247C480, { master, kId, kRow, name, code });
    if (g.registered) return;
    g.registered = true;
    // the key registry: Marduk's entries, with Rick's own body files
    const uint32_t registry = GRead32(base, kRegistryPtr);
    const uint32_t regCode = s + 384;
    Call(ctx, base, sub_82429C58, { regCode, g.code });
    for (const Reg& r : kDonorRegistry)
    {
        uint32_t k = r.key;
        if (r.op == Op::File && r.type == 0) k = Crc("ric.nud");
        if (r.op == Op::File && r.type == 1) k = Crc("ric.nut");
        if (r.op == Op::File && r.type == 2) k = Crc("ric.bon");
        if (r.op == Op::File && r.type == 6) k = Crc("ric.xml");
        GWrite32(base, key, k);
        if (r.op == Op::Code) Call(ctx, base, sub_8247DDB0, { registry, regCode });
        else if (r.op == Op::File) Call(ctx, base, sub_8247A628, { registry, regCode, r.type, key });
        else Call(ctx, base, sub_82472220, { registry, regCode, r.type, key, r.index });
    }
    Call(ctx, base, sub_82336FC0, { regCode, 0 });
    std::fprintf(stderr, "[rick] registered 'ric' (registry %08X, chara master %08X)\n", registry, master);
}

bool Ours(uint32_t record) { return On() && g.ready && (record == kRecord0 || record == kRecord0 + 1); }
uint32_t RecordAddr(uint32_t record) { return g.records + (record - kRecord0) * kRecordSize; }

// The loader's stand-in (see sub_82331B50): Rick's records answer Marduk's id while it reads the code table.
int g_proxy = 0;
} // namespace

PPC_FUNC(sub_82468AD0)
{
    const uint32_t master = ctx.r3.u32;
    __imp__sub_82468AD0(ctx, base);
    if (On()) Register(ctx, base, master);
}

PPC_FUNC(sub_8246A054)
{
    const uint32_t master = ctx.r3.u32;
    __imp__sub_8246A054(ctx, base);
    if (On()) Register(ctx, base, master);
}

#define RECORD_FIELD(addr, value)                                                                                \
    PPC_FUNC(sub_##addr)                                                                                         \
    {                                                                                                            \
        if (Ours(ctx.r3.u32)) { const uint32_t r = RecordAddr(ctx.r3.u32); (void)r; ctx.r3.u64 = (value); return; } \
        __imp__sub_##addr(ctx, base);                                                                            \
    }
RECORD_FIELD(822761A0, r)
RECORD_FIELD(822762A8, GRead32(base, r + 4))
RECORD_FIELD(822762E0, g_proxy ? kDonorId : GRead32(base, r + 0))
RECORD_FIELD(82276310, GRead32(base, r + 12))
RECORD_FIELD(82276380, GRead32(base, r + 8))
RECORD_FIELD(82276408, GRead32(base, r + 80))
#undef RECORD_FIELD

PPC_FUNC(sub_82276270)                      // the record's +20 function: Marduk's
{
    if (Ours(ctx.r3.u32)) ctx.r3.u64 = kDonorRecord0 + (ctx.r3.u32 - kRecord0);
    __imp__sub_82276270(ctx, base);
}

void RickLendPortraits(uint8_t* base);
PPC_FUNC(sub_82276348)
{
    if (On() && g.ready && ctx.r3.u32 == kId) { RickLendPortraits(base); ctx.r3.u64 = GRead32(base, g.records + 8); return; }
    __imp__sub_82276348(ctx, base);
}

PPC_FUNC(sub_822761D0)
{
    if (On() && g.ready && ctx.r3.u32 == kId) { ctx.r3.u64 = 2; return; }
    __imp__sub_822761D0(ctx, base);
}

PPC_FUNC(sub_82276200)
{
    if (On() && g.ready && ctx.r3.u32 == kId) { ctx.r3.u64 = kRecord0; return; }
    __imp__sub_82276200(ctx, base);
}

int g_pickProxy = 0;                        // sub_8227DC40 runs for Rick with Marduk's id: his records answer it
PPC_FUNC(sub_82276218)
{
    if (On() && g.ready && (ctx.r3.u32 == kId || (g_pickProxy && ctx.r3.u32 == kDonorId))) { ctx.r3.u64 = kRecord0 + (ctx.r4.u32 < 2 ? ctx.r4.u32 : 0); return; }
    __imp__sub_82276218(ctx, base);
}

PPC_FUNC(sub_82276440)
{
    if (On() && g.ready && ctx.r3.u32 == kRow) { ctx.r3.u64 = kRecord0; return; }
    __imp__sub_82276440(ctx, base);
}

PPC_FUNC(sub_82331B50)                      // (players, slot, record, ...): reads kCodes[id] with id < 63
{
    if (!Ours(ctx.r5.u32)) { __imp__sub_82331B50(ctx, base); return; }
    const uint32_t slot = kCodes + 4 * kDonorId, donorCode = GRead32(base, slot);
    GWrite32(base, slot, g.code);
    ++g_proxy;
    __imp__sub_82331B50(ctx, base);
    --g_proxy;
    GWrite32(base, slot, donorCode);
    std::fprintf(stderr, "[rick] loaded player %u from record %u (result %u)\n", ctx.r4.u32, 0u, ctx.r3.u32);
}

extern "C" PPC_FUNC(__imp__sub_82276760);
PPC_FUNC(sub_82276760)                      // can id be picked (ids above 58: never)
{
    const uint32_t id = ctx.r3.u32, lr = uint32_t(ctx.lr);
    if (On() && g.ready && id == kId) ctx.r3.u64 = 1;
    else __imp__sub_82276760(ctx, base);
    static uint32_t logged = 0;
    if (On() && (id == kId || id == kDonorId) && logged++ < 40)
        std::fprintf(stderr, "[rick] can pick %u -> %u (lr %08X)\n", id, ctx.r3.u32, lr);
}

extern "C" PPC_FUNC(__imp__sub_82276628);
PPC_FUNC(sub_82276628)                      // sets a player (r3) up from its record (+88): with Marduk's, then Rick's id
{
    const uint32_t player = ctx.r3.u32, record = GRead32(base, player + 88);
    if (!Ours(record)) { __imp__sub_82276628(ctx, base); return; }
    GWrite32(base, player + 88, kDonorRecord0 + (record - kRecord0));
    __imp__sub_82276628(ctx, base);
    GWrite32(base, player + 88, record);
    GWrite32(base, player + 84, kId);
    GWrite32(base, player + 80, kRow);
    std::fprintf(stderr, "[rick] player %08X set up from record %u\n", player, record);
}

extern "C" PPC_FUNC(__imp__sub_8227DC40);
PPC_FUNC(sub_8227DC40)                      // a pick (?, player r4, ..., id r7): first tests the id's bit in the
{                                           // player's mask at +328, which no id above 63 has (sld by 64 is 0)
    if (!(On() && g.ready && ctx.r7.u32 == kId)) { __imp__sub_8227DC40(ctx, base); return; }
    const uint32_t player = ctx.r4.u32;
    const uint64_t bit = 1ull << kDonorId;
    const uint64_t mask = (uint64_t(GRead32(base, player + 328)) << 32) | GRead32(base, player + 332);
    const uint64_t lent = mask | bit;
    GWrite32(base, player + 328, uint32_t(lent >> 32));
    GWrite32(base, player + 332, uint32_t(lent));
    ctx.r7.u64 = kDonorId;
    ++g_pickProxy;
    __imp__sub_8227DC40(ctx, base);
    --g_pickProxy;
    const uint64_t now = (uint64_t(GRead32(base, player + 328)) << 32) | GRead32(base, player + 332);
    const uint64_t back = (now & ~bit) | (mask & bit);      // Marduk's own bit as it was
    GWrite32(base, player + 328, uint32_t(back >> 32));
    GWrite32(base, player + 332, uint32_t(back));
    std::fprintf(stderr, "[rick] pick by player %08X -> %u (player +64 = %u, record %u)\n", player, ctx.r3.u32,
                 GRead32(base, player + 64), GRead32(base, player + 404));
}

extern "C" PPC_FUNC(__imp__sub_82554F08);
PPC_FUNC(sub_82554F08)                      // bitset (r3: {count, ..., bits}) set(id r4): asserts id < count
{
    if (On() && g.ready && ctx.r4.u32 == kId && ctx.r4.u32 >= GRead32(base, ctx.r3.u32))
    {
        static uint32_t logged = 0;
        if (logged++ < 20)
            std::fprintf(stderr, "[rick] bitset %08X (count %u) set(%u) -> Marduk's bit, lr %08X\n", ctx.r3.u32,
                         GRead32(base, ctx.r3.u32), ctx.r4.u32, uint32_t(ctx.lr));
        ctx.r4.u64 = kDonorId;
    }
    __imp__sub_82554F08(ctx, base);
}

// Portraits: the portrait code (sub_8262B9A0: screen r3, member r4) finds a member's UI row through sub_82276348
// and its two pictures' keys in a table by row; for Rick, Marduk's row of the table holds Rick's keys meanwhile.
namespace {
constexpr uint32_t kPortraitKeys = 0x820CD408, kDonorUiRow = 18;
uint32_t g_portraitScope = 0, g_lentKeys[2] = {}, g_lent = 0;
}
extern "C" PPC_FUNC(__imp__sub_8262B9A0);
PPC_FUNC(sub_8262B9A0)
{
    ++g_portraitScope;
    __imp__sub_8262B9A0(ctx, base);
    --g_portraitScope;
    if (g_lent)
    {
        for (uint32_t s = 0; s < 2; ++s) GWrite32(base, kPortraitKeys + 4 * (2 * kDonorUiRow + s), g_lentKeys[s]);
        g_lent = 0;
    }
}
void RickLendPortraits(uint8_t* base)       // from sub_82276348 (id 64) inside sub_8262B9A0
{
    if (!g_portraitScope || g_lent) return;
    for (uint32_t s = 0; s < 2; ++s)
    {
        const uint32_t at = kPortraitKeys + 4 * (2 * kDonorUiRow + s);
        g_lentKeys[s] = GRead32(base, at);
        GWrite32(base, at, Crc(s ? "ric/portrait_2p.nut" : "ric/portrait_1p.nut"));
    }
    g_lent = 1;
}
