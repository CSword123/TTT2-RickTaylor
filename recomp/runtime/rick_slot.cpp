// Rick Taylor as an added fighter of his own (TTT2-RickTaylor project; design after Petexy's Wii U port, whose
// runtime/src/title/roster.cpp does this for its character packs). TTT2_RICK=1 turns it on.
//
// Rick is internal id 64 (the title's ids end at 62; 63 means random/none), records 140 and 141 (copies of
// Marduk's, held here), motion row 57 (a row no record uses) and code "ric": his body files ric.nud/.nut/.bon/.xml
// come from the title update's overlay (ttt2rick.ttt2.overlay), his moveset is Marduk's under a key of its own and
// his motion pack Marduk's with his own stance (ttt2rick.convert.idle).
// Addresses: recomp/ROSTER.md.
#include "kernel_shared.h"
#include "guest_heap.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <set>
#include <tuple>
#include <utility>

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
constexpr uint32_t kId = 64, kRecord0 = 140, kRow = 57, kDonorId = 17, kDonorRecord0 = 36, kDonorRow = 17;
constexpr uint32_t kRecords = 0x82DC21B8, kRecordSize = 84, kTitleRecords = 139;
constexpr uint32_t kMotionRows = 0x820A24B0;            // 68 x {motion pack, moveset, move list} (sub_82590690)
constexpr uint32_t kCodes = 0x82DD1CC8;                  // 63 x char*, by internal id
constexpr uint32_t kGrids = 0x8200C8BC;                  // {cells, count} by mode
constexpr uint32_t kRegistryPtr = 0x82EE0B5C;
constexpr uint32_t kMovesetKey = 0x52494331;             // "RIC1": Marduk's moveset with Rick's id, from the overlay
constexpr uint32_t kRickMotions = 0x52494332;            // "RIC2": Marduk's motion pack with Rick's stance
constexpr uint32_t kJenMotions = 0x4A454E32;             // "JEN2": RIC2 with Jennifer's feet planted (ttt2jen.motions)
constexpr uint32_t kDonorMoveList = 0x68A7CEF7;

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

// TTT2_RICK_BLOOD=1: Rick's textures with Splatterhouse's blood on his jeans and shoes, and his portraits with the
// picture's (ttt2rick.convert.clean takes it off by default).
bool Bloody()
{
    static const bool on = [] { const char* e = std::getenv("TTT2_RICK_BLOOD"); return e && *e == '1'; }();
    return on;
}

// TTT2_JEN=1 (with TTT2_RICK=1): Rick's slot gets Jennifer's body (jen.nud/.nut/.bon/.xml, ttt2jen.convert) and her
// motion pack (JEN2), keeping his moves, name and portraits: a way to play her until she has a slot of her own.
bool Jen()
{
    static const bool on = [] { const char* e = std::getenv("TTT2_JEN"); return e && *e == '1'; }();
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
    uint32_t labels = 0;            // 4 x 128 bytes: label names with Rick's code (sub_82B62BE8)
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
    g.labels = Alloc(base, 4 * 128);

    if (kRow != 17)                          // a row of his own (not while he shares Marduk's)
    {
        const uint32_t row = kMotionRows + 12 * kRow;
        GWrite32(base, row + 0, Jen() ? kJenMotions : kRickMotions);
        GWrite32(base, row + 4, kMovesetKey);
        GWrite32(base, row + 8, kDonorMoveList);
    }

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
        if (r.op == Op::File && r.type == 0) k = Crc(Jen() ? "jen.nud" : "ric.nud");
        if (r.op == Op::File && r.type == 1) k = Crc(Jen() ? "jen.nut" : Bloody() ? "ric_blood.nut" : "ric.nut");
        if (r.op == Op::File && r.type == 2) k = Crc(Jen() ? "jen.bon" : "ric.bon");
        if (r.op == Op::File && r.type == 6) k = Crc(Jen() ? "jen.xml" : "ric.xml");
        GWrite32(base, key, k);
        if (r.op == Op::Code) Call(ctx, base, sub_8247DDB0, { registry, regCode });
        else if (r.op == Op::File) Call(ctx, base, sub_8247A628, { registry, regCode, r.type, key });
        else Call(ctx, base, sub_82472220, { registry, regCode, r.type, key, r.index });
    }
    Call(ctx, base, sub_82336FC0, { regCode, 0 });
    std::fprintf(stderr, "[rick] registered 'ric' (registry %08X, chara master %08X)%s\n", registry, master,
                 Jen() ? ": Jennifer's body and motions (TTT2_JEN=1)" : "");
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

void LogOddRecord(const char* fn, uint32_t record, uint32_t lr)
{
    static uint32_t logged = 0;
    if (On() && record >= kTitleRecords && !(record == kRecord0 || record == kRecord0 + 1) && logged++ < 40)
        std::fprintf(stderr, "[rick] %s(record %u) out of range, lr %08X\n", fn, record, lr);
}
#define RECORD_FIELD(addr, value)                                                                                \
    PPC_FUNC(sub_##addr)                                                                                         \
    {                                                                                                            \
        if (Ours(ctx.r3.u32)) { const uint32_t r = RecordAddr(ctx.r3.u32); (void)r; ctx.r3.u64 = (value); return; } \
        LogOddRecord(#addr, ctx.r3.u32, uint32_t(ctx.lr));                                                       \
        __imp__sub_##addr(ctx, base);                                                                            \
    }
RECORD_FIELD(822761A0, r)
RECORD_FIELD(822762A8, GRead32(base, r + 4))
RECORD_FIELD(822762E0, g_proxy ? kDonorId : GRead32(base, r + 0))
RECORD_FIELD(82276310, GRead32(base, r + 12))
RECORD_FIELD(82276408, GRead32(base, r + 80))
#undef RECORD_FIELD

// Rick has Marduk's UI row (the row of every table of the 2D screens and the HUD). The screens ask a member's row
// (sub_82276348 by id, sub_82276380 by record) and then use that row's entries; until the next question, the
// entries of Marduk's row that Rick has his own of are his:
// - the fights' HUD (sub_823D55A8 faces, sub_823D6738 names) takes its pictures' numbers from a table by row
//   (0x82DDD2F0: {name, face 1p, face 2p}) to sub_823D11B8 (HUD container 7C476BDE = resource 176): Marduk's
//   numbers become Rick's own, appended to the container by ttt2rick.convert.hud;
// - the 2D layouts' per-fighter labels (chara_face_mar, p1_chara_waku_mar, ...), whatever table they come from,
//   reach sub_82B62BE8 (a sprite's jump to a label by name): Marduk's become Rick's (chara_face_ric, ...), which
//   ttt2rick.convert.layouts adds to every layout that has Marduk's.
namespace {
constexpr uint32_t kHudResource = 176, kHudDonor[3] = { 48, 123, 182 }, kHudRick[3] = { 259, 260, 261 };
bool g_askedRick = false;
}
PPC_FUNC(sub_82276380)                      // record -> +8 UI row
{
    g_askedRick = Ours(ctx.r3.u32);
    if (g_askedRick) { ctx.r3.u64 = GRead32(base, RecordAddr(ctx.r3.u32) + 8); return; }
    LogOddRecord("82276380", ctx.r3.u32, uint32_t(ctx.lr));
    __imp__sub_82276380(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_823D11B8);
PPC_FUNC(sub_823D11B8)                      // a HUD picture (r4 resource, r5 number, ...)
{
    if (g_askedRick && ctx.r4.u32 == kHudResource)
        for (uint32_t k = 0; k < 3; ++k)
            if (ctx.r5.u32 == kHudDonor[k]) { ctx.r5.u64 = kHudRick[k]; break; }
    __imp__sub_823D11B8(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_82B62BE8);
PPC_FUNC(sub_82B62BE8)                      // (sprite r3, label name r4): jump to the label
{
    const uint32_t name = ctx.r4.u32;
    if (g_askedRick && g.ready && name)
    {
        const char* text = reinterpret_cast<const char*>(base + name);
        const size_t n = strnlen(text, 120);
        for (size_t at = 0; at + 3 <= n; ++at)  // the code token: "mar" between '_' (or the ends)
            if (std::memcmp(text + at, "mar", 3) == 0 && (at == 0 || text[at - 1] == '_') &&
                (at + 3 == n || text[at + 3] == '_'))
            {
                static uint32_t ring = 0;
                const uint32_t copy = g.labels + 128 * (ring++ & 3);
                std::memcpy(base + copy, text, n + 1);
                std::memcpy(base + copy + at, "ric", 3);
                ctx.r4.u64 = copy;
                if (std::getenv("TTT2_RICK_TRACE"))
                    std::fprintf(stderr, "[rick] label %s -> %s, lr %08X\n", text,
                                 reinterpret_cast<const char*>(base + copy), uint32_t(ctx.lr));
                break;
            }
    }
    __imp__sub_82B62BE8(ctx, base);
}

PPC_FUNC(sub_82276270)                      // the record's +20 function: Marduk's
{
    if (Ours(ctx.r3.u32)) ctx.r3.u64 = kDonorRecord0 + (ctx.r3.u32 - kRecord0);
    __imp__sub_82276270(ctx, base);
}

void RickLendPortraits(uint8_t* base);
PPC_FUNC(sub_82276348)
{
    const uint32_t id = ctx.r3.u32, lr = uint32_t(ctx.lr);
    g_askedRick = On() && g.ready && id == kId;
    if (g_askedRick) { RickLendPortraits(base); ctx.r3.u64 = GRead32(base, g.records + 8); }
    else __imp__sub_82276348(ctx, base);
    if (std::getenv("TTT2_RICK_TRACE"))
    {
        static std::set<std::pair<uint32_t, uint32_t>> seen;
        if (seen.size() < 3000 && seen.emplace(id, lr).second)
            std::fprintf(stderr, "[rick] id_to_row(%u) = %u lr %08X\n", id, ctx.r3.u32, lr);
    }
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
bool g_rickPickedElsewhere = false;         // Rick picked through sub_8227DC40 (any pick, the dummy's too)
PPC_FUNC(sub_82276218)
{
    if (On() && g.ready && (ctx.r3.u32 == kId || (g_pickProxy && ctx.r3.u32 == kDonorId))) { ctx.r3.u64 = kRecord0 + (ctx.r4.u32 < 2 ? ctx.r4.u32 : 0); return; }
    __imp__sub_82276218(ctx, base);
}

PPC_FUNC(sub_82276440)
{
    if (On() && g.ready && kRow != kDonorRow && ctx.r3.u32 == kRow) { ctx.r3.u64 = kRecord0; return; }
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

// The pick gate (sub_82276760: can id r3 be picked) needs no override since TTT2-Recomp 0.2.5 hooks it itself
// (classic_offline.cpp, wrapping the title's): the title's answers an id out of 0-62 as Paul's (always yes).

extern "C" PPC_FUNC(__imp__sub_82276628);
PPC_FUNC(sub_82276628)                      // sets a player (r3) up from its record (+88): with Marduk's, then Rick's id
{
    const uint32_t player = ctx.r3.u32, record = GRead32(base, player + 88);
    if (!Ours(record)) { __imp__sub_82276628(ctx, base); return; }
    const uint32_t donor = kDonorRecord0 + (record - kRecord0), donorRow = kRecords + donor * kRecordSize + 12;
    GWrite32(base, player + 88, donor);
    GWrite32(base, donorRow, kRow);                         // it loads the motion data by the record's row
    __imp__sub_82276628(ctx, base);
    GWrite32(base, donorRow, kDonorRow);
    GWrite32(base, player + 88, record);
    GWrite32(base, player + 84, kId);
    GWrite32(base, player + 80, kRow);
    std::fprintf(stderr, "[rick] player %08X set up from record %u\n", player, record);
}

extern "C" PPC_FUNC(__imp__sub_82590690);
PPC_FUNC(sub_82590690)                      // (holder r3, row r4): its three resources from the row's keys
{
    if (On() && (ctx.r4.u32 == kRow || ctx.r4.u32 == kDonorRow))
    {
        static uint32_t logged = 0;
        const uint32_t row = kMotionRows + 12 * ctx.r4.u32;
        if (logged++ < 20)
            std::fprintf(stderr, "[rick] motion row %u: %08X %08X %08X (holder %08X, lr %08X)\n", ctx.r4.u32,
                         GRead32(base, row), GRead32(base, row + 4), GRead32(base, row + 8), ctx.r3.u32,
                         uint32_t(ctx.lr));
    }
    __imp__sub_82590690(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_8227DC40);
PPC_FUNC(sub_8227DC40)                      // a pick (?, player r4, ..., id r7): first tests the id's bit in the
{                                           // player's mask at +328, which no id above 63 has (sld by 64 is 0)
    if (!(On() && g.ready && ctx.r7.u32 == kId)) { __imp__sub_8227DC40(ctx, base); return; }
    const uint32_t player = ctx.r4.u32;
    // One Rick per team: the title keeps a fighter out of the second member by its cleared bit in this mask; Rick
    // has no bit and Marduk's lent one is put back after his pick, so while a member's record (+348 / +352) is
    // already Rick's the pick goes through with his own id 64, whose bit test fails as for any unavailable fighter.
    if (Ours(GRead32(base, player + 348)) || Ours(GRead32(base, player + 352)))
    {
        static uint32_t logged = 0;
        if (logged++ < 5) std::fprintf(stderr, "[rick] second Rick in the team refused (player %08X)\n", player);
        __imp__sub_8227DC40(ctx, base);
        return;
    }
    const uint64_t bit = 1ull << kDonorId;
    const uint64_t mask = (uint64_t(GRead32(base, player + 328)) << 32) | GRead32(base, player + 332);
    const uint64_t lent = mask | bit;
    GWrite32(base, player + 328, uint32_t(lent >> 32));
    GWrite32(base, player + 332, uint32_t(lent));
    ctx.r7.u64 = kDonorId;
    ++g_pickProxy;
    __imp__sub_8227DC40(ctx, base);
    --g_pickProxy;
    if (ctx.r3.u32) g_rickPickedElsewhere = true;
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

// His portrait files (ttt2rick.convert.portrait): ric/<name>.nut, ric/<name>_blood.nut under TTT2_RICK_BLOOD=1.
namespace {
const char* PortraitFile(const char* name)
{
    static char path[64];
    std::snprintf(path, sizeof(path), "ric/%s%s.nut", name, Bloody() ? "_blood" : "");
    return path;
}
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
        GWrite32(base, at, Crc(PortraitFile(s ? "portrait_2p" : "portrait_1p")));
    }
    g_lent = 1;
}

// The loading/VS screens' portrait set (sub_82711E78: object r3, internal id r4) copies a fighter's keys from the
// key tables by its UI row: for Rick, his own pictures (the main one and, for the alternate kinds Marduk has, the
// green one).
extern "C" PPC_FUNC(__imp__sub_82711E78);
PPC_FUNC(sub_82711E78)
{
    const uint32_t obj = ctx.r3.u32, id = ctx.r4.u32;
    if (On()) std::fprintf(stderr, "[rick] portrait set %08X for id %u, lr %08X\n", obj, id, uint32_t(ctx.lr));
    __imp__sub_82711E78(ctx, base);
    if (!(On() && g.ready && id == kId)) return;
    GWrite32(base, obj + 0, Crc(PortraitFile("portrait_1p")));
    for (uint32_t off : { 12u, 24u, 36u })
        if (GRead32(base, obj + off)) GWrite32(base, obj + off, Crc(PortraitFile("portrait_green")));
    std::fprintf(stderr, "[rick] portrait set %08X: Rick's\n", obj);
}

extern "C" PPC_FUNC(__imp__sub_82584ED0);
PPC_FUNC(sub_82584ED0)                      // (table r3, index r4): its entry is set; asserts index < count
{
    const uint32_t count = GRead32(base, GRead32(base, ctx.r3.u32 + 68) + 12);
    if (On() && g.ready && ctx.r4.u32 == kId && ctx.r4.u32 >= count)
    {
        static uint32_t logged = 0;
        if (logged++ < 20)
            std::fprintf(stderr, "[rick] table %08X (count %u) [%u] -> Marduk's, lr %08X\n", ctx.r3.u32, count,
                         ctx.r4.u32, uint32_t(ctx.lr));
        ctx.r4.u64 = kDonorId;
    }
    __imp__sub_82584ED0(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_825550C8);
PPC_FUNC(sub_825550C8)                      // (?, id r4, data r5): the save data's per-fighter entry (Tag25SaveData,
{                                           // at a pick): tests it by id (sub_82584ED0), then writes it with the id
    if (On() && g.ready && ctx.r4.u32 == kId)   // itself (sub_82584F08), out of its 63 for Rick: Marduk's entry
    {
        static uint32_t logged = 0;
        if (logged++ < 20)
            std::fprintf(stderr, "[rick] save entry (%08X, %u) -> Marduk's, lr %08X\n", ctx.r3.u32, ctx.r4.u32,
                         uint32_t(ctx.lr));
        ctx.r4.u64 = kDonorId;
    }
    __imp__sub_825550C8(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_8258CAE8);
PPC_FUNC(sub_8258CAE8)                      // a per-fighter counter (u16[59] r3, row r4) += r5: none for Rick (it
{                                           // would write past the array)
    if (On() && ctx.r4.u32 >= 59) return;
    __imp__sub_8258CAE8(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_822763B0);
PPC_FUNC(sub_822763B0)                      // record whose +8 (UI row) is r3: logged for odd rows
{
    const uint32_t row = ctx.r3.u32, lr = uint32_t(ctx.lr);
    __imp__sub_822763B0(ctx, base);
    static uint32_t logged = 0;
    if (On() && row >= 59 && logged++ < 40) std::fprintf(stderr, "[rick] row->record(%u) = %u, lr %08X\n", row, ctx.r3.u32, lr);
}

// The pick handler (sub_8227CFC0: cursor r3, record r4) stores the fighter's id in the match set-up's member byte
// and caps it at 62 (zkb, a Fight Lab mob): for Rick the byte gets 64 back, so the screens after the select (VS,
// loading) find him and not row 0 (Paul).
// Later copies of the members (about a dozen functions, as on Wii U) cap the byte again: while Rick is picked, a
// member byte holding 62 is his. (62 is otherwise only Fight Lab's mob.) Rick stays picked until another fighter is
// picked into his member byte: a tag partner's pick has a byte of its own and must not end it (it did, and the VS
// and promotion screens showed row 0, Paul, for Rick).
namespace { uint32_t g_inPick = 0, g_pickByte = 0; std::set<uint32_t> g_rickBytes; }
extern bool g_rickPickedElsewhere;
extern "C" PPC_FUNC(__imp__sub_822815E0);
PPC_FUNC(sub_822815E0)                      // a side's member (side r3, member r4) -> its byte (id at +0)
{
    const uint32_t side = ctx.r3.u32, member = ctx.r4.u32, lr = uint32_t(ctx.lr);
    __imp__sub_822815E0(ctx, base);
    if (std::getenv("TTT2_RICK_TRACE") && ctx.r3.u32)
    {
        static std::set<std::tuple<uint32_t, uint32_t, uint32_t>> seen;
        if (seen.size() < 200 && seen.emplace(side, member, lr).second)
            std::fprintf(stderr, "[rick] member byte (side %08X, member %u) = %u at %08X, lr %08X%s\n", side, member,
                         base[ctx.r3.u32], ctx.r3.u32, lr, g_inPick ? " (pick)" : "");
    }
    if (g_inPick) g_pickByte = ctx.r3.u32;
    // a pick that is not the player's own (the Practice dummy's, a CPU's) stores the capped 62 without
    // sub_8227CFC0: sub_8227DC40 marks Rick picked there (62 is otherwise only Fight Lab's mob)
    else if ((!g_rickBytes.empty() || g_rickPickedElsewhere) && ctx.r3.u32 && base[ctx.r3.u32] == 62)
        base[ctx.r3.u32] = uint8_t(kId);
}
extern "C" PPC_FUNC(__imp__sub_8227CFC0);
PPC_FUNC(sub_8227CFC0)
{
    const uint32_t record = ctx.r4.u32;
    ++g_inPick;
    g_pickByte = 0;
    __imp__sub_8227CFC0(ctx, base);
    --g_inPick;
    if (On() && g.ready && record < kTitleRecords && g_pickByte) g_rickBytes.erase(g_pickByte);
    if (Ours(record) && g_pickByte)
    {
        g_rickBytes.insert(g_pickByte);
        base[g_pickByte] = uint8_t(kId);
        std::fprintf(stderr, "[rick] member byte %08X = %u\n", g_pickByte, kId);
    }
}

// The select screen's big portraits: sub_8262BEE0 (lister r3) lists container 6CCDFC60's frames, by UI row, in two
// vectors {first, last, end} at +4 (player 1's frames) and +24 (player 2's); sub_8262B2D0 (lister r3, row r4, slot
// r5: player * 2 + member) shows one. Rick's two frames follow the container's own (118, 119: ttt2rick.convert.
// portrait; the bloody two 120, 121); while a slot showing Rick is drawn, Marduk's row of its vector holds Rick's frame. Whose a slot is
// comes from the select screen (sub_826409E0: screen r3): its player object (*(*(screen + 148) + 48 / 56)) holds
// the members' records at +348 / +352, and before a pick the cursor's fighter id (sub_8227AE48(player)).
namespace {
constexpr uint32_t kPortraitKey = 0x6CCDFC60, kPortraitFrame = 118;
uint32_t g_lister = 0, g_rickFrames[2] = {}, g_selectScreen = 0;
}
extern "C" PPC_FUNC(__imp__sub_8262BEE0);
extern "C" PPC_FUNC(__imp__sub_82A827F8);
PPC_FUNC(sub_8262BEE0)
{
    const uint32_t lister = ctx.r3.u32;
    __imp__sub_8262BEE0(ctx, base);
    if (!(On() && g.ready)) return;
    GWrite32(base, g.scratch + 512, kPortraitKey);                      // the container, as the lister finds it
    Call(ctx, base, __imp__sub_82A827F8, { GRead32(base, lister + 44), g.scratch + 512 });
    const uint32_t entry = ctx.r3.u32, container = entry ? GRead32(base, entry) : 0;
    g_lister = 0;
    const uint32_t first = kPortraitFrame + (Bloody() ? 2 : 0);
    if (!container || GRead32(base, container) < first + 2) return;
    for (uint32_t p = 0; p < 2; ++p)
        g_rickFrames[p] = container + GRead32(base, container + 4 + 8 * (first + p));
    g_lister = lister;
    std::fprintf(stderr, "[rick] select portraits: lister %08X, container %08X\n", lister, container);
}

extern "C" PPC_FUNC(__imp__sub_826409E0);
PPC_FUNC(sub_826409E0)
{
    g_selectScreen = ctx.r3.u32;
    __imp__sub_826409E0(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_8227AE48);
bool SlotIsRick(PPCContext& ctx, uint8_t* base, uint32_t slot)
{
    if (!g_selectScreen) return false;
    const uint32_t players = GRead32(base, g_selectScreen + 148);
    const uint32_t player = players ? GRead32(base, players + (slot < 2 ? 48 : 56)) : 0;
    if (!player) return false;
    const uint32_t record = GRead32(base, player + 348 + 4 * (slot & 1));
    bool rick = Ours(record);
    uint32_t id = ~0u;
    // before its pick a member shows the cursor's fighter: the first member, or the second once the first is picked
    // (the first's record is set: below kTitleRecords; 139 = none)
    const bool choosing = (slot & 1) == 0 || GRead32(base, player + 348) < kTitleRecords ||
                          Ours(GRead32(base, player + 348));
    if (!rick && choosing && record >= kTitleRecords && !Ours(record))
    {
        Call(ctx, base, __imp__sub_8227AE48, { player });
        id = ctx.r3.u32;
        rick = id == kId;
    }
    static uint32_t logged = 0;
    if (std::getenv("TTT2_RICK_TRACE") && logged++ < 60)
        std::fprintf(stderr, "[rick] portrait slot %u: record %u, cursor id %d -> %s\n", slot, record, int(id),
                     rick ? "Rick" : "not Rick");
    return rick;
}

extern "C" PPC_FUNC(__imp__sub_8262B2D0);
PPC_FUNC(sub_8262B2D0)
{
    const uint32_t lister = ctx.r3.u32, row = ctx.r4.u32, slot = ctx.r5.u32;
    uint32_t at = 0, theirs = 0;
    if (On() && g_lister == lister && row == kDonorUiRow && slot < 4)
    {
        const PPCContext saved = ctx;
        const bool rick = SlotIsRick(ctx, base, slot);
        ctx = saved;
        if (rick)
        {
            const uint32_t first = GRead32(base, lister + (slot < 2 ? 4 : 24));
            at = first + 4 * row;
            theirs = GRead32(base, at);
            GWrite32(base, at, g_rickFrames[slot < 2 ? 0 : 1]);
        }
    }
    __imp__sub_8262B2D0(ctx, base);
    if (at) GWrite32(base, at, theirs);
}

// The profile's per-fighter records (tk::profile::PartsCS::EachFighterInfoCS, Array<, 63>, 76 bytes each at
// profile +9216): sub_82659F48 (profile r3) updates the team members' records after a match, by each member's id
// byte (profile +640 + member * 4288). Rick's 64 indexed past the array (an ignored assert) and overwrote the
// profile data after it, and the next Arcade load after a continue never finished. While it runs, Rick's byte is
// Marduk's id: his results go to Marduk's record (as the other per-fighter save entry, sub_825550C8).
extern "C" PPC_FUNC(__imp__sub_82659F48);
PPC_FUNC(sub_82659F48)
{
    const uint32_t profile = ctx.r3.u32;
    uint32_t lent[2] = {};
    for (uint32_t k = 0; k < 2; ++k)
        if (On() && g.ready && profile && base[profile + 640 + 4288 * k] == kId)
        {
            lent[k] = 1;
            base[profile + 640 + 4288 * k] = uint8_t(kDonorId);
        }
    __imp__sub_82659F48(ctx, base);
    for (uint32_t k = 0; k < 2; ++k)
        if (lent[k]) base[profile + 640 + 4288 * k] = uint8_t(kId);
    if (lent[0] || lent[1]) std::fprintf(stderr, "[rick] profile %08X: fighter record as Marduk's\n", profile);
}

// The other accessors of the same per-fighter tables (count at *(table + 68) + 12; an index past it is the title's
// deliberate store to address 0) used when the save data is updated after a match, as sub_82584ED0: Rick's id is
// Marduk's there. Their failed checks were the null writes after a lost Arcade match, after which the next match's
// load (on continue) never finished.
namespace {
void RickTableIndex(uint8_t* base, uint32_t table, PPCRegister& index, uint32_t lr, const char* fn)
{
    if (!(On() && g.ready && index.u32 == kId && table)) return;
    const uint32_t info = GRead32(base, table + 68);
    if (info && index.u32 < GRead32(base, info + 12)) return;
    static uint32_t logged = 0;
    if (logged++ < 20) std::fprintf(stderr, "[rick] %s table %08X [64] -> Marduk's, lr %08X\n", fn, table, lr);
    index.u64 = kDonorId;
}
}
extern "C" PPC_FUNC(__imp__sub_82584E88);
PPC_FUNC(sub_82584E88)                      // (table r3, index r4): the entry, asserted set
{
    RickTableIndex(base, ctx.r3.u32, ctx.r4, uint32_t(ctx.lr), "82584E88");
    __imp__sub_82584E88(ctx, base);
}
extern "C" PPC_FUNC(__imp__sub_82585230);
PPC_FUNC(sub_82585230)                      // (table r3, index r4, ...)
{
    RickTableIndex(base, ctx.r3.u32, ctx.r4, uint32_t(ctx.lr), "82585230");
    __imp__sub_82585230(ctx, base);
}
extern "C" PPC_FUNC(__imp__sub_82585590);
PPC_FUNC(sub_82585590)                      // (table r3, ..., index r7, ...)
{
    RickTableIndex(base, ctx.r3.u32, ctx.r7, uint32_t(ctx.lr), "82585590");
    __imp__sub_82585590(ctx, base);
}



// A player's body collision (sub_822FB4F8: player r3) takes a per-fighter pointer by id from two 64-entry tables
// (0x82DD0A68, and 0x82DD0B68 in some down states), read without a bound: Rick's 64 got the second table's first
// entry, and a downed Rick could not be hit (found 2026-10-25 by bisecting the functions that read player +84;
// Rick's files under Marduk's id 17 were hit). While it runs, Rick's id is Marduk's.
extern "C" PPC_FUNC(__imp__sub_822FB4F8);
PPC_FUNC(sub_822FB4F8)
{
    const uint32_t player = ctx.r3.u32;
    const bool lend = On() && g.ready && player && GRead32(base, player + 84) == kId;
    if (lend) GWrite32(base, player + 84, kDonorId);
    __imp__sub_822FB4F8(ctx, base);
    if (lend) GWrite32(base, player + 84, kId);
}

// TTT2_RICK_GRIDTRACE=1: the select grids' cell lookups (sub_8227A0D8: grids r3 (mode at +76), cell r4) and the
// cursor's fighter (sub_8227AE48: player r3), each distinct (mode, caller) once
extern "C" PPC_FUNC(__imp__sub_8227A0D8);
PPC_FUNC(sub_8227A0D8)
{
    static const bool on = std::getenv("TTT2_RICK_GRIDTRACE") != nullptr;
    if (on)
    {
        static std::set<std::pair<uint32_t, uint32_t>> seen;
        const uint32_t mode = GRead32(base, ctx.r3.u32 + 76), lr = uint32_t(ctx.lr);
        if (seen.size() < 100 && seen.emplace(mode, lr).second)
            std::fprintf(stderr, "[rick] grid cell (grids %08X mode %u, cell %d) lr %08X\n", ctx.r3.u32, mode,
                         int32_t(ctx.r4.u32), lr);
    }
    __imp__sub_8227A0D8(ctx, base);
}
