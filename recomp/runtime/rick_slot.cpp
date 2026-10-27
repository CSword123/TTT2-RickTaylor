// The added fighters, each with a roster slot of its own: Rick Taylor and Jennifer Willis (TTT2-RickTaylor project;
// design after Petexy's Wii U port, whose runtime/src/title/roster.cpp does this for its character packs).
// TTT2_RICK=1 turns them on (TTT2_JEN=0 leaves Jennifer out).
//
// Each added fighter (kFighters) has an internal id from 64 on (the title's ids end at 62; 63 means random/none), two
// records from 140 on (copies of Marduk's, held here), a motion row no record uses, a code and a select grid cell in
// the top row, right of Violet's. Its body files <code>.nud/.nut/.bon/.xml come from the title update's overlay
// (ttt2rick.ttt2.overlay), its moveset is Marduk's under a key of its own (Rick's attacks, ttt2rick.convert.slot;
// Jennifer's is Rick's with her id, ttt2jen.slot) and its motion pack Marduk's with its own stance
// (ttt2rick.convert.idle; Jennifer's: ttt2jen.motions). Everything else of the title's that is by fighter is
// Marduk's for them (his records' fields, his UI row with their own pictures lent to it, his voice, his save entries).
// Addresses: recomp/ROSTER.md.
#include "kernel_shared.h"
#include "guest_heap.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iterator>
#include <set>
#include <string>
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
constexpr uint32_t kDonorId = 17, kDonorRecord0 = 36, kDonorRow = 17;
constexpr uint32_t kRecords = 0x82DC21B8, kRecordSize = 84, kTitleRecords = 139;
constexpr uint32_t kMotionRows = 0x820A24B0;            // 68 x {motion pack, moveset, move list} (sub_82590690)
constexpr uint32_t kCodes = 0x82DD1CC8;                  // 63 x char*, by internal id
constexpr uint32_t kGrids = 0x8200C8BC;                  // {cells, count} by mode
constexpr uint32_t kRegistryPtr = 0x82EE0B5C;
constexpr uint32_t kDonorMoveList = 0x68A7CEF7;
constexpr uint32_t kTitleCells = 62;                     // the full grids' (modes 1 and 2) own cells

struct Fighter
{
    const char* code;
    const char* name;
    uint32_t id, record0, row;
    uint32_t motions, moveset;      // their keys ("RIC2" / "RIC1"): the motion row's first two
    const char* nud; const char* nut; const char* nutBlood; const char* bon; const char* xml;
    const char* mop;                // its skeleton's spring-bone file (registry type 3), or nullptr: Marduk's
    uint32_t portraitFrame;         // its first frame in the select portraits' container (ttt2rick.convert.portrait)
    uint32_t hud[3];                // its HUD numbers: name, face 1p, face 2p (ttt2rick.convert.hud)
    int32_t column;                 // its grid cell's column in the top row
    const char* codeB;              // costume B's code (its second record), with body files <codeB>.nud/.nut/.bon/.xml
                                    // of their own (ttt2rick.convert.slot), or nullptr: costume B is costume A
    // at run time
    bool on;
    uint32_t records, codeAddr, codeAddrB;
    uint32_t masterCode;            // the text of its code in its chara master entry (MasterCodeText), or 0
    int32_t cell;
    uint32_t frames[2];             // its select portraits (guest addresses), when the lister has them
};

// Rick: Marduk's moveset with Splatterhouse's attacks, his body on Marduk's skeleton. Jennifer: Rick's moveset and
// motions (her feet planted), her body on Nina's skeleton (with Nina's spring-bone file for the bust's OPT bone).
Fighter kFighters[] = {
    { "ric", "Rick", 64, 140, 57, 0x52494332, 0x52494331, "ric.nud", "ric.nut", "ric_blood.nut", "ric.bon", "ric.xml",
      nullptr, 118, { 259, 260, 261 }, 19, "rib" },     // costume B: Mirror Rick
    { "jen", "Jennifer", 65, 142, 58, 0x4A454E32, 0x4A454E31, "jen.nud", "jen.nut", nullptr, "jen.bon", "jen.xml",
      "nin.mop", 122, { 262, 263, 264 }, 20, nullptr },
};

// Marduk's registry entries (sub_8244E618), replayed for an added fighter's code with its own body files' keys.
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

bool Env(const char* name, bool otherwise)
{
    const char* e = std::getenv(name);
    return e && *e ? *e == '1' : otherwise;
}

bool On()
{
    static const bool on = Env("TTT2_RICK", false);
    return on;
}

// TTT2_RICK_BLOOD=1: Rick's textures with Splatterhouse's blood on his jeans and shoes, and his portraits with the
// picture's (ttt2rick.convert.clean takes it off by default).
bool Bloody()
{
    static const bool on = Env("TTT2_RICK_BLOOD", false);
    return on;
}

bool Traced()
{
    static const bool on = std::getenv("TTT2_RICK_TRACE") != nullptr;
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

struct State
{
    uint32_t scratch = 0;           // string objects and keys for the guest calls
    uint32_t labels = 0;            // 4 x 128 bytes: label names with an added fighter's code (sub_82B62BE8)
    bool ready = false, registered = false;
} g;

Fighter* ById(uint32_t id)
{
    if (!(On() && g.ready)) return nullptr;
    for (Fighter& f : kFighters)
        if (f.on && f.id == id) return &f;
    return nullptr;
}

Fighter* ByRecord(uint32_t record)
{
    if (!(On() && g.ready)) return nullptr;
    for (Fighter& f : kFighters)
        if (f.on && (record == f.record0 || record == f.record0 + 1)) return &f;
    return nullptr;
}

Fighter* ByRow(uint32_t row)
{
    if (!(On() && g.ready)) return nullptr;
    for (Fighter& f : kFighters)
        if (f.on && f.row == row) return &f;
    return nullptr;
}

uint32_t RecordAddr(const Fighter& f, uint32_t record) { return f.records + (record - f.record0) * kRecordSize; }

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

// One-time set-up: the records, the motion rows and the grids.
void Prepare(uint8_t* base)
{
    if (g.ready) return;
    g.ready = true;
    kFighters[0].on = true;
    kFighters[1].on = Env("TTT2_JEN", true);
    for (Fighter& f : kFighters)
    {
        if (!f.on) continue;
        f.records = Alloc(base, 2 * kRecordSize);
        for (uint32_t k = 0; k < 2; ++k)
        {
            const uint32_t r = f.records + k * kRecordSize;
            std::memcpy(base + r, base + kRecords + (kDonorRecord0 + k) * kRecordSize, kRecordSize);
            GWrite32(base, r + 0, f.id);
            GWrite32(base, r + 12, f.row);
        }
        f.codeAddr = Alloc(base, 16);
        std::memcpy(base + f.codeAddr, f.code, std::strlen(f.code) + 1);
        if (f.codeB)
        {
            f.codeAddrB = Alloc(base, 16);
            std::memcpy(base + f.codeAddrB, f.codeB, std::strlen(f.codeB) + 1);
        }
        const uint32_t row = kMotionRows + 12 * f.row;
        GWrite32(base, row + 0, f.motions);
        GWrite32(base, row + 4, f.moveset);
        GWrite32(base, row + 8, kDonorMoveList);
    }
    g.scratch = Alloc(base, 1024);
    g.labels = Alloc(base, 4 * 128);

    // The full grids (modes 1 and 2: 62 cells, the top row columns 3-18) get a cell per added fighter: at its column
    // of the top row (19, 20: right of Violet's), in the row's ring (between cell 61 and cell 46) and above the
    // middle row's cell of its column (cell = column), below the bottom row's (cell 23 + column).
    Fighter* on[std::size(kFighters)];
    uint32_t n = 0;
    for (Fighter& f : kFighters)
        if (f.on) on[n++] = &f;
    for (uint32_t mode = 1; mode <= 2; ++mode)
    {
        const uint32_t entry = kGrids + 8 * mode, cells = GRead32(base, entry), count = GRead32(base, entry + 4);
        if (count != kTitleCells) continue;
        const uint32_t copy = Alloc(base, 32 * (kTitleCells + n));
        std::memcpy(base + copy, base + cells, 32 * kTitleCells);
        for (uint32_t k = 0; k < n; ++k)
        {
            const int32_t cell = int32_t(kTitleCells + k), col = on[k]->column;
            const int32_t left = k ? cell - 1 : 61, right = k + 1 < n ? cell + 1 : 46;
            const int32_t fields[8] = { int32_t(on[k]->id), 51, 23 + col, col, left, right, col, 0 };
            for (int i = 0; i < 8; ++i) GWrite32(base, copy + 32 * cell + 4 * i, uint32_t(fields[i]));
            GWrite32(base, copy + 32 * col + 8, uint32_t(cell));           // the middle row's: up
            GWrite32(base, copy + 32 * (23 + col) + 12, uint32_t(cell));    // the bottom row's: down
            on[k]->cell = cell;
        }
        if (n)
        {
            GWrite32(base, copy + 32 * 61 + 20, kTitleCells);               // cell 61's right
            GWrite32(base, copy + 32 * 46 + 16, kTitleCells + n - 1);       // cell 46's left
        }
        GWrite32(base, entry, copy);
        GWrite32(base, entry + 4, kTitleCells + n);
    }
    for (const Fighter& f : kFighters)
        if (f.on)
            std::fprintf(stderr, "[added] %s: id %u, records %u/%u at %08X, motion row %u, code '%s', cell %d\n",
                         f.name, f.id, f.record0, f.record0 + 1, f.records, f.row, f.code, f.cell);
}

// The chara master (+4: a std::map by id, its head node at +8; node: left +0, parent +4, right +8, id +12; the head is
// the nil node) keeps one
// entry per id, and a loadPlayer command finds its fighter there by code: the text of the code string in the
// fighter's entry (an inline std::string: text +0, length +16), for costume B's code to be swapped in at its loads.
uint32_t MasterCodeText(uint8_t* base, uint32_t master, const Fighter& f)
{
    const uint32_t head = GRead32(base, master + 8);
    uint32_t n = GRead32(base, head + 4);
    for (int depth = 0; n && n != head && depth < 64; ++depth)
    {
        const uint32_t id = GRead32(base, n + 12);
        if (id == f.id)
        {
            const size_t len = std::strlen(f.code);
            for (uint32_t s = n + 16; s < n + 512; s += 4)
                if (std::memcmp(base + s, f.code, len + 1) == 0 && GRead32(base, s + 16) == len)
                    return s;
            return 0;
        }
        n = GRead32(base, n + (f.id < id ? 0 : 8));
    }
    return 0;
}

void Register(PPCContext& ctx, uint8_t* base, uint32_t master)
{
    Prepare(base);
    const uint32_t s = g.scratch;
    const uint32_t name = s, code = s + 128, text = s + 256, key = s + 288, regCode = s + 384;
    const uint32_t registry = GRead32(base, kRegistryPtr);
    const bool first = !g.registered;
    g.registered = true;
    for (Fighter& f : kFighters)
    {
        if (!f.on) continue;
        // the chara master: {id, motion row, name, code}
        std::memcpy(base + text, f.name, std::strlen(f.name) + 1);
        Call(ctx, base, sub_823011F8, { name, text });
        Call(ctx, base, sub_823011F8, { code, f.codeAddr });
        Call(ctx, base, sub_8247C480, { master, f.id, f.row, name, code });
        if (f.codeB)
        {
            f.masterCode = MasterCodeText(base, master, f);
            std::fprintf(stderr, "[added] %s: chara master code text at %08X\n", f.name, f.masterCode);
        }
        if (!first) continue;
        // the key registry: Marduk's entries, with the fighter's own body files (and costume B's code with its own)
        for (int b = 0; b < (f.codeB ? 2 : 1); ++b)
        {
            const char* c = b ? f.codeB : f.code;
            const std::string nud = std::string(c) + ".nud", nut = std::string(c) + ".nut";
            const std::string nutBlood = std::string(c) + "_blood.nut", bon = std::string(c) + ".bon";
            const std::string xml = std::string(c) + ".xml";
            Call(ctx, base, sub_82429C58, { regCode, b ? f.codeAddrB : f.codeAddr });
            for (const Reg& r : kDonorRegistry)
            {
                uint32_t k = r.key;
                if (r.op == Op::File && r.type == 0) k = Crc(nud.c_str());
                if (r.op == Op::File && r.type == 1) k = Crc(Bloody() && f.nutBlood ? nutBlood.c_str() : nut.c_str());
                if (r.op == Op::File && r.type == 2) k = Crc(bon.c_str());
                if (r.op == Op::File && r.type == 3 && f.mop) k = Crc(f.mop);
                if (r.op == Op::File && r.type == 6) k = Crc(xml.c_str());
                GWrite32(base, key, k);
                if (r.op == Op::Code) Call(ctx, base, sub_8247DDB0, { registry, regCode });
                else if (r.op == Op::File) Call(ctx, base, sub_8247A628, { registry, regCode, r.type, key });
                else Call(ctx, base, sub_82472220, { registry, regCode, r.type, key, r.index });
            }
            Call(ctx, base, sub_82336FC0, { regCode, 0 });
            std::fprintf(stderr, "[added] registered '%s' (registry %08X, chara master %08X)\n", c, registry, master);
        }
    }
}

// The loader's stand-in (see sub_82331B50): an added fighter's records answer Marduk's id while it reads the code table.
int g_proxy = 0;
// The costume each pick (player, member) was made in: its select cursor's byte +380 + member (the costume panel's
// 1 = A, 2 = B, then the saved costumes), noted with the pick (NotePick).
uint8_t g_costumes[2][2] = {};
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
    if (On() && record >= kTitleRecords && !ByRecord(record) && logged++ < 40)
        std::fprintf(stderr, "[added] %s(record %u) out of range, lr %08X\n", fn, record, lr);
}
#define RECORD_FIELD(addr, value)                                                                                \
    PPC_FUNC(sub_##addr)                                                                                         \
    {                                                                                                            \
        if (const Fighter* f = ByRecord(ctx.r3.u32))                                                             \
        {                                                                                                        \
            const uint32_t r = RecordAddr(*f, ctx.r3.u32);                                                       \
            (void)r;                                                                                             \
            ctx.r3.u64 = (value);                                                                                \
            return;                                                                                              \
        }                                                                                                        \
        LogOddRecord(#addr, ctx.r3.u32, uint32_t(ctx.lr));                                                       \
        __imp__sub_##addr(ctx, base);                                                                            \
    }
RECORD_FIELD(822761A0, r)
RECORD_FIELD(822762A8, GRead32(base, r + 4))
RECORD_FIELD(822762E0, g_proxy ? kDonorId : GRead32(base, r + 0))
RECORD_FIELD(82276310, GRead32(base, r + 12))
RECORD_FIELD(82276408, GRead32(base, r + 80))
#undef RECORD_FIELD

// The added fighters have Marduk's UI row (the row of every table of the 2D screens and the HUD). The screens ask a
// member's row (sub_82276348 by id, sub_82276380 by record) and then use that row's entries; until the next question,
// the entries of Marduk's row that the fighter asked about has its own of are its own:
// - the fights' HUD (sub_823D55A8 faces, sub_823D6738 names) takes its pictures' numbers from a table by row
//   (0x82DDD2F0: {name, face 1p, face 2p}) to sub_823D11B8 (HUD container 7C476BDE = resource 176): Marduk's
//   numbers become the fighter's own, appended to the container by ttt2rick.convert.hud;
// - the 2D layouts' per-fighter labels (chara_face_mar, p1_chara_waku_mar, ...), whatever table they come from,
//   reach sub_82B62BE8 (a sprite's jump to a label by name): Marduk's become the fighter's (chara_face_ric,
//   chara_face_jen, ...), which ttt2rick.convert.layouts adds to every layout that has Marduk's.
namespace {
constexpr uint32_t kHudResource = 176, kHudDonor[3] = { 48, 123, 182 };
const Fighter* g_asked = nullptr;
// Once both members are picked, the select screen (sub_82643A08) hides the second when the two have the same UI row:
// Rick, Jennifer and Marduk share Marduk's row 18. There the second member's record questions (kSecondSites) answer
// Steve's row 17 (kAliasRow) when the first is another of the three, and Steve's labels (`ste`) and big portrait
// are the second member's (sub_826278E0, sub_8262B2D0). While the second is still being chosen, SelectSecondMembers
// draws it instead (the rank bar takes its stats by row: Steve's row would show Steve's).
constexpr uint32_t kAliasRow = 17;
constexpr uint32_t kFirstSites[] = { 0x82643DE8, 0x82643DF8, 0x82643E70, 0x82643E9C };
constexpr uint32_t kSecondSites[] = { 0x82643E3C, 0x82643E7C, 0x82643EC8 };
bool g_inSelect = false;
int g_firstKey = -3;                        // the first member: an added fighter's index, -1 Marduk, -3 anyone else
int RecordKey(uint32_t record)
{
    for (int k = 0; k < int(std::size(kFighters)); ++k)
        if (kFighters[k].on && g.ready && (record == kFighters[k].record0 || record == kFighters[k].record0 + 1))
            return k;
    return record == kDonorRecord0 || record == kDonorRecord0 + 1 ? -1 : -3;
}
bool SelectAlias(uint32_t lr, uint32_t record)
{
    if (!g_inSelect) return false;
    for (uint32_t x : kFirstSites) if (x == lr) { g_firstKey = RecordKey(record); return false; }
    for (uint32_t x : kSecondSites)
        if (x == lr)
        {
            const int key = RecordKey(record);
            return key != -3 && g_firstKey != -3 && key != g_firstKey;
        }
    return false;
}
}
PPC_FUNC(sub_82276380)                      // record -> +8 UI row
{
    if (SelectAlias(uint32_t(ctx.lr), ctx.r3.u32)) { ctx.r3.u64 = kAliasRow; return; }
    g_asked = ByRecord(ctx.r3.u32);
    if (g_asked) { ctx.r3.u64 = GRead32(base, RecordAddr(*g_asked, ctx.r3.u32) + 8); return; }
    LogOddRecord("82276380", ctx.r3.u32, uint32_t(ctx.lr));
    __imp__sub_82276380(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_823D11B8);
PPC_FUNC(sub_823D11B8)                      // a HUD picture (r4 resource, r5 number, ...)
{
    if (g_asked && ctx.r4.u32 == kHudResource)
        for (uint32_t k = 0; k < 3; ++k)
            if (ctx.r5.u32 == kHudDonor[k]) { ctx.r5.u64 = g_asked->hud[k]; break; }
    __imp__sub_823D11B8(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_82B62BE8);
const char* g_labelFrom = nullptr;          // a code token renamed in labels, and what to (sub_826278E0's scope)
const char* g_labelTo = nullptr;
PPC_FUNC(sub_82B62BE8)                      // (sprite r3, label name r4): jump to the label
{
    const uint32_t name = ctx.r4.u32;
    // the code token to replace ("mar") and what with
    const char* from = nullptr; const char* to = nullptr;
    const char* text = name ? reinterpret_cast<const char*>(base + name) : "";
    const size_t n = strnlen(text, 120);
    auto token = [&](const char* code) {
        for (size_t at = 0; at + 3 <= n; ++at)  // the code token between '_' (or the ends)
            if (std::memcmp(text + at, code, 3) == 0 && (at == 0 || text[at - 1] == '_') &&
                (at + 3 == n || text[at + 3] == '_'))
                return int(at);
        return -1;
    };
    int at = -1;
    if (g_labelFrom && (at = token(g_labelFrom)) >= 0) { from = g_labelFrom; to = g_labelTo; }
    else if (g_asked && (at = token("mar")) >= 0) { from = "mar"; to = g_asked->code; }
    if (from && g.ready)
    {
        static uint32_t ring = 0;
        const uint32_t copy = g.labels + 128 * (ring++ & 3);
        std::memcpy(base + copy, text, n + 1);
        std::memcpy(base + copy + at, to, 3);
        ctx.r4.u64 = copy;
        if (Traced())
            std::fprintf(stderr, "[added] label %s -> %s, lr %08X\n", text,
                         reinterpret_cast<const char*>(base + copy), uint32_t(ctx.lr));
    }
    __imp__sub_82B62BE8(ctx, base);
}

PPC_FUNC(sub_82276270)                      // the record's +20 function: Marduk's
{
    if (const Fighter* f = ByRecord(ctx.r3.u32)) ctx.r3.u64 = kDonorRecord0 + (ctx.r3.u32 - f->record0);
    __imp__sub_82276270(ctx, base);
}

void AddedLendPortraits(uint8_t* base, const Fighter& f);
PPC_FUNC(sub_82276348)
{
    const uint32_t id = ctx.r3.u32, lr = uint32_t(ctx.lr);
    if (g_inSelect && lr == kFirstSites[0])
        g_firstKey = ById(id) ? int(ById(id) - kFighters) : id == kDonorId ? -1 : -3;
    g_asked = ById(id);
    if (g_asked) { AddedLendPortraits(base, *g_asked); ctx.r3.u64 = GRead32(base, g_asked->records + 8); }
    else __imp__sub_82276348(ctx, base);
    if (Traced())
    {
        static std::set<std::pair<uint32_t, uint32_t>> seen;
        if (seen.size() < 3000 && seen.emplace(id, lr).second)
            std::fprintf(stderr, "[added] id_to_row(%u) = %u lr %08X\n", id, ctx.r3.u32, lr);
    }
}

PPC_FUNC(sub_822761D0)
{
    if (ById(ctx.r3.u32)) { ctx.r3.u64 = 2; return; }
    __imp__sub_822761D0(ctx, base);
}

PPC_FUNC(sub_82276200)
{
    if (const Fighter* f = ById(ctx.r3.u32)) { ctx.r3.u64 = f->record0; return; }
    __imp__sub_82276200(ctx, base);
}

const Fighter* g_pickProxy = nullptr;      // sub_8227DC40 runs for an added fighter with Marduk's id: its records answer
PPC_FUNC(sub_82276218)
{
    const Fighter* f = ById(ctx.r3.u32);
    if (!f && g_pickProxy && ctx.r3.u32 == kDonorId) f = g_pickProxy;
    if (f) { ctx.r3.u64 = f->record0 + (ctx.r4.u32 < 2 ? ctx.r4.u32 : 0); return; }
    __imp__sub_82276218(ctx, base);
}

PPC_FUNC(sub_82276440)
{
    if (const Fighter* f = ByRow(ctx.r3.u32)) { ctx.r3.u64 = f->record0; return; }
    __imp__sub_82276440(ctx, base);
}

PPC_FUNC(sub_82331B50)                      // (players, slot, record, ...): reads kCodes[id] with id < 63
{
    const Fighter* f = ByRecord(ctx.r5.u32);
    if (!f) { __imp__sub_82331B50(ctx, base); return; }
    const uint32_t slot = kCodes + 4 * kDonorId, donorCode = GRead32(base, slot);
    const uint32_t s = ctx.r4.u32;          // slot: player + 2 * member
    const bool costumeB = f->codeB && s < 4 && g_costumes[s % 2][s / 2] == 2;     // picked in costume B: its own code
    GWrite32(base, slot, costumeB ? f->codeAddrB : f->codeAddr);
    if (f->masterCode)                      // the command's code must match its chara master entry's (same length)
        std::memcpy(base + f->masterCode, costumeB ? f->codeB : f->code, std::strlen(f->code));
    ++g_proxy;
    __imp__sub_82331B50(ctx, base);
    --g_proxy;
    GWrite32(base, slot, donorCode);
    std::fprintf(stderr, "[added] loaded player %u as %s%s (result %u)\n", ctx.r4.u32, f->name,
                 costumeB ? " (costume B)" : "", ctx.r3.u32);
}

// The pick gate (sub_82276760: can id r3 be picked) needs no override since TTT2-Recomp 0.2.5 hooks it itself
// (classic_offline.cpp, wrapping the title's): the title's answers an id out of 0-62 as Paul's (always yes).

extern "C" PPC_FUNC(__imp__sub_82276628);
PPC_FUNC(sub_82276628)                      // sets a player (r3) up from its record (+88): with Marduk's, then its id
{
    const uint32_t player = ctx.r3.u32, record = GRead32(base, player + 88);
    const Fighter* f = ByRecord(record);
    if (!f) { __imp__sub_82276628(ctx, base); return; }
    const uint32_t donor = kDonorRecord0 + (record - f->record0), donorRow = kRecords + donor * kRecordSize + 12;
    GWrite32(base, player + 88, donor);
    GWrite32(base, donorRow, f->row);                       // it loads the motion data by the record's row
    __imp__sub_82276628(ctx, base);
    GWrite32(base, donorRow, kDonorRow);
    GWrite32(base, player + 88, record);
    GWrite32(base, player + 84, f->id);
    GWrite32(base, player + 80, f->row);
    std::fprintf(stderr, "[added] player %08X set up as %s from record %u\n", player, f->name, record);
}

extern "C" PPC_FUNC(__imp__sub_82590690);
PPC_FUNC(sub_82590690)                      // (holder r3, row r4): its three resources from the row's keys
{
    if (On() && (ByRow(ctx.r4.u32) || ctx.r4.u32 == kDonorRow))
    {
        static uint32_t logged = 0;
        const uint32_t row = kMotionRows + 12 * ctx.r4.u32;
        if (logged++ < 20)
            std::fprintf(stderr, "[added] motion row %u: %08X %08X %08X (holder %08X, lr %08X)\n", ctx.r4.u32,
                         GRead32(base, row), GRead32(base, row + 4), GRead32(base, row + 8), ctx.r3.u32,
                         uint32_t(ctx.lr));
    }
    __imp__sub_82590690(ctx, base);
}

// The picks, as the select screen commits them (player, member): the id whose member byte the title's copies cap
// at 62 (sub_822815E0). A select cursor (player object) has its player at +320 and the members picked so far at +340.
namespace {
uint32_t g_picks[2][2] = {};
void NotePick(uint8_t* base, uint32_t cursor, uint32_t member, uint32_t id)
{
    const uint32_t player = GRead32(base, cursor + 320);
    if (player < 2 && member < 2)
    {
        g_picks[player][member] = ById(id) ? id : 0;
        g_costumes[player][member] = base[cursor + 380 + member];
        if (Traced())
            std::fprintf(stderr, "[added] pick: player %u member %u in costume %u\n", player, member,
                         g_costumes[player][member]);
    }
}
}

extern "C" PPC_FUNC(__imp__sub_8227DC40);
PPC_FUNC(sub_8227DC40)                      // a pick (?, player r4, ..., id r7): first tests the id's bit in the
{                                           // player's mask at +328, which no id above 63 has (sld by 64 is 0)
    const uint32_t cursor = ctx.r4.u32, id = ctx.r7.u32, member = cursor ? GRead32(base, cursor + 340) : 2;
    const Fighter* f = ById(id);
    if (!f)
    {
        __imp__sub_8227DC40(ctx, base);
        if (ctx.r3.u32 && On() && g.ready) NotePick(base, cursor, member, id);
        return;
    }
    // One of each per team: the title keeps a fighter out of the second member by its cleared bit in this mask; an
    // added fighter has no bit and Marduk's lent one is put back after its pick, so while a member's record
    // (+348 / +352) is already this fighter's the pick goes through with its own id, whose bit test fails as for any
    // unavailable fighter.
    if (ByRecord(GRead32(base, cursor + 348)) == f || ByRecord(GRead32(base, cursor + 352)) == f)
    {
        static uint32_t logged = 0;
        if (logged++ < 5) std::fprintf(stderr, "[added] second %s in the team refused (player %08X)\n", f->name, cursor);
        __imp__sub_8227DC40(ctx, base);
        return;
    }
    const uint64_t bit = 1ull << kDonorId;
    const uint64_t mask = (uint64_t(GRead32(base, cursor + 328)) << 32) | GRead32(base, cursor + 332);
    const uint64_t lent = mask | bit;
    GWrite32(base, cursor + 328, uint32_t(lent >> 32));
    GWrite32(base, cursor + 332, uint32_t(lent));
    ctx.r7.u64 = kDonorId;
    const Fighter* outer = g_pickProxy;
    g_pickProxy = f;
    __imp__sub_8227DC40(ctx, base);
    g_pickProxy = outer;
    if (ctx.r3.u32) NotePick(base, cursor, member, f->id);
    const uint64_t now = (uint64_t(GRead32(base, cursor + 328)) << 32) | GRead32(base, cursor + 332);
    const uint64_t back = (now & ~bit) | (mask & bit);      // Marduk's own bit as it was
    GWrite32(base, cursor + 328, uint32_t(back >> 32));
    GWrite32(base, cursor + 332, uint32_t(back));
    std::fprintf(stderr, "[added] pick of %s by player %u (cursor %08X), member %u -> %u (record %u)\n", f->name,
                 GRead32(base, cursor + 320), cursor, member, ctx.r3.u32, GRead32(base, cursor + 404));
}

extern "C" PPC_FUNC(__imp__sub_82554F08);
PPC_FUNC(sub_82554F08)                      // bitset (r3: {count, ..., bits}) set(id r4): asserts id < count
{
    if (ById(ctx.r4.u32) && ctx.r4.u32 >= GRead32(base, ctx.r3.u32))
    {
        static uint32_t logged = 0;
        if (logged++ < 20)
            std::fprintf(stderr, "[added] bitset %08X (count %u) set(%u) -> Marduk's bit, lr %08X\n", ctx.r3.u32,
                         GRead32(base, ctx.r3.u32), ctx.r4.u32, uint32_t(ctx.lr));
        ctx.r4.u64 = kDonorId;
    }
    __imp__sub_82554F08(ctx, base);
}

// Portrait files (ttt2rick.convert.portrait): <code>/<name>.nut; Rick's <name>_blood.nut under TTT2_RICK_BLOOD=1.
namespace {
const char* PortraitFile(const Fighter& f, const char* name)
{
    static char path[64];
    std::snprintf(path, sizeof(path), "%s/%s%s.nut", f.code, name, Bloody() && f.nutBlood ? "_blood" : "");
    return path;
}
}

// Portraits: the portrait code (sub_8262B9A0: screen r3, member r4) finds a member's UI row through sub_82276348
// and its two pictures' keys in a table by row; for an added fighter, Marduk's row of the table holds its keys
// meanwhile.
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
void AddedLendPortraits(uint8_t* base, const Fighter& f)   // from sub_82276348 (an added id) inside sub_8262B9A0
{
    if (!g_portraitScope) return;
    for (uint32_t s = 0; s < 2; ++s)
    {
        const uint32_t at = kPortraitKeys + 4 * (2 * kDonorUiRow + s);
        if (!g_lent) g_lentKeys[s] = GRead32(base, at);
        GWrite32(base, at, Crc(PortraitFile(f, s ? "portrait_2p" : "portrait_1p")));
    }
    g_lent = 1;
}

// The loading/VS screens' portrait set (sub_82711E78: object r3, internal id r4) copies a fighter's keys from the
// key tables by its UI row: for an added fighter, its own pictures (the main one and, for the alternate kinds Marduk
// has, the green one).
extern "C" PPC_FUNC(__imp__sub_82711E78);
PPC_FUNC(sub_82711E78)
{
    const uint32_t obj = ctx.r3.u32, id = ctx.r4.u32;
    if (On()) std::fprintf(stderr, "[added] portrait set %08X for id %u, lr %08X\n", obj, id, uint32_t(ctx.lr));
    __imp__sub_82711E78(ctx, base);
    const Fighter* f = ById(id);
    if (!f) return;
    GWrite32(base, obj + 0, Crc(PortraitFile(*f, "portrait_1p")));
    for (uint32_t off : { 12u, 24u, 36u })
        if (GRead32(base, obj + off)) GWrite32(base, obj + off, Crc(PortraitFile(*f, "portrait_green")));
    std::fprintf(stderr, "[added] portrait set %08X: %s's\n", obj, f->name);
}

extern "C" PPC_FUNC(__imp__sub_82584ED0);
PPC_FUNC(sub_82584ED0)                      // (table r3, index r4): its entry is set; asserts index < count
{
    const uint32_t count = GRead32(base, GRead32(base, ctx.r3.u32 + 68) + 12);
    if (ById(ctx.r4.u32) && ctx.r4.u32 >= count)
    {
        static uint32_t logged = 0;
        if (logged++ < 20)
            std::fprintf(stderr, "[added] table %08X (count %u) [%u] -> Marduk's, lr %08X\n", ctx.r3.u32, count,
                         ctx.r4.u32, uint32_t(ctx.lr));
        ctx.r4.u64 = kDonorId;
    }
    __imp__sub_82584ED0(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_825550C8);
PPC_FUNC(sub_825550C8)                      // (?, id r4, data r5): the save data's per-fighter entry (Tag25SaveData,
{                                           // at a pick): tests it by id (sub_82584ED0), then writes it with the id
    if (ById(ctx.r4.u32))                   // itself (sub_82584F08), out of its 63 for an added id: Marduk's entry
    {
        static uint32_t logged = 0;
        if (logged++ < 20)
            std::fprintf(stderr, "[added] save entry (%08X, %u) -> Marduk's, lr %08X\n", ctx.r3.u32, ctx.r4.u32,
                         uint32_t(ctx.lr));
        ctx.r4.u64 = kDonorId;
    }
    __imp__sub_825550C8(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_8258CAE8);
PPC_FUNC(sub_8258CAE8)                      // a per-fighter counter (u16[59] r3, row r4) += r5: none for an added
{                                           // fighter (it would write past the array)
    if (On() && ctx.r4.u32 >= 59) return;
    __imp__sub_8258CAE8(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_822763B0);
PPC_FUNC(sub_822763B0)                      // record whose +8 (UI row) is r3: logged for odd rows
{
    const uint32_t row = ctx.r3.u32, lr = uint32_t(ctx.lr);
    __imp__sub_822763B0(ctx, base);
    static uint32_t logged = 0;
    if (On() && row >= 59 && logged++ < 40) std::fprintf(stderr, "[added] row->record(%u) = %u, lr %08X\n", row, ctx.r3.u32, lr);
}

// The pick handler (sub_8227CFC0: cursor r3, record r4) stores the fighter's id in the match set-up's member byte
// (sub_822815E0(side + 640, member): side = the player's, *(manager + 60 + 4 * player)) and caps it at 62 (zkb, a
// Fight Lab mob): for an added fighter the byte gets its id back, so the screens after the select (VS, loading) find
// it and not row 0 (Paul).
// Later copies of the members (about a dozen functions, as on Wii U) cap the byte again: a member byte holding 62 is
// the added fighter that player picked as that member (g_picks; 62 is otherwise only Fight Lab's mob). For a byte
// outside the players' sides (a copy elsewhere), the member's pick when only one added fighter is picked as it.
namespace {
constexpr uint32_t kManagerPtr = 0x82E6C5A8;              // *(*kManagerPtr + 256): the sides' manager (sub_82653478)
uint32_t g_inPick = 0, g_pickByte = 0;

int PlayerOfSide(uint8_t* base, uint32_t side)
{
    const uint32_t root = GRead32(base, kManagerPtr), manager = root ? GRead32(base, root + 256) : 0;
    if (!manager) return -1;
    for (uint32_t p = 0; p < 2; ++p)
        if (GRead32(base, manager + 60 + 4 * p) == side) return int(p);
    return -1;
}

uint32_t PickedAs(uint8_t* base, uint32_t side, uint32_t member)
{
    if (member >= 2) return 0;
    const int p = PlayerOfSide(base, side);
    if (p >= 0) return g_picks[p][member];
    const uint32_t a = g_picks[0][member], b = g_picks[1][member];
    return a && b && a != b ? 0 : (a ? a : b);
}
}
extern "C" PPC_FUNC(__imp__sub_822815E0);
PPC_FUNC(sub_822815E0)                      // a side's member (side + 640 r3, member r4) -> its byte (id at +0)
{
    const uint32_t side = ctx.r3.u32 - 640, member = ctx.r4.u32, lr = uint32_t(ctx.lr);
    __imp__sub_822815E0(ctx, base);
    if (!(On() && g.ready) || !ctx.r3.u32) return;
    if (Traced())
    {
        static std::set<std::tuple<uint32_t, uint32_t, uint32_t>> seen;
        if (seen.size() < 200 && seen.emplace(side, member, lr).second)
            std::fprintf(stderr, "[added] member byte (side %08X = player %d, member %u) = %u at %08X, lr %08X%s\n",
                         side, PlayerOfSide(base, side), member, base[ctx.r3.u32], ctx.r3.u32, lr,
                         g_inPick ? " (pick)" : "");
    }
    if (g_inPick) g_pickByte = ctx.r3.u32;
    else if (base[ctx.r3.u32] == 62)
        if (const uint32_t id = PickedAs(base, side, member)) base[ctx.r3.u32] = uint8_t(id);
}
extern "C" PPC_FUNC(__imp__sub_8227CFC0);
PPC_FUNC(sub_8227CFC0)
{
    const uint32_t cursor = ctx.r3.u32, record = ctx.r4.u32, member = GRead32(base, cursor + 340);
    ++g_inPick;
    g_pickByte = 0;
    __imp__sub_8227CFC0(ctx, base);
    --g_inPick;
    if (!(On() && g.ready)) return;
    const Fighter* f = ByRecord(record);
    if (record < kTitleRecords || f) NotePick(base, cursor, member, f ? f->id : 0);
    if (f && g_pickByte)
    {
        base[g_pickByte] = uint8_t(f->id);
        std::fprintf(stderr, "[added] member byte %08X = %u (%s, player %u member %u)\n", g_pickByte, f->id, f->name,
                     GRead32(base, cursor + 320), member);
    }
}

// The select screen's big portraits: sub_8262BEE0 (lister r3) lists container 6CCDFC60's frames, by UI row, in two
// vectors {first, last, end} at +4 (player 1's frames) and +24 (player 2's); sub_8262B2D0 (lister r3, row r4, slot
// r5: player * 2 + member) shows one. The added fighters' frames follow the container's own (Rick's 118, 119, his
// bloody two 120, 121; Jennifer's 122, 123: ttt2rick.convert.portrait); while a slot showing one of them is drawn,
// Marduk's row of its vector holds that fighter's frame. Whose a slot is comes from the select screen (sub_826409E0:
// screen r3): its player object (*(*(screen + 148) + 48 / 56)) holds the members' records at +348 / +352, and before
// a pick the cursor's fighter id (sub_8227AE48(player)).
namespace {
constexpr uint32_t kPortraitKey = 0x6CCDFC60;
uint32_t g_lister = 0, g_selectScreen = 0;
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
    if (!container) return;
    for (Fighter& f : kFighters)
    {
        const uint32_t first = f.portraitFrame + (Bloody() && f.nutBlood ? 2 : 0);
        if (!f.on || GRead32(base, container) < first + 2) { f.frames[0] = f.frames[1] = 0; continue; }
        for (uint32_t p = 0; p < 2; ++p)
            f.frames[p] = container + GRead32(base, container + 4 + 8 * (first + p));
    }
    g_lister = lister;
    std::fprintf(stderr, "[added] select portraits: lister %08X, container %08X (%u frames)\n", lister, container,
                 GRead32(base, container));
}

extern "C" PPC_FUNC(__imp__sub_826409E0);
PPC_FUNC(sub_826409E0)
{
    g_selectScreen = ctx.r3.u32;
    const uint32_t slot = ctx.r4.u32, row = ctx.r5.u32, lr = uint32_t(ctx.lr);
    __imp__sub_826409E0(ctx, base);
    if (Traced()) std::fprintf(stderr, "[added] big portrait slot %u row %u -> %u, lr %08X\n", slot, row, ctx.r3.u32, lr);
}

extern "C" PPC_FUNC(__imp__sub_8227AE48);
const Fighter* SlotFighter(PPCContext& ctx, uint8_t* base, uint32_t slot)
{
    if (!g_selectScreen) return nullptr;
    const uint32_t players = GRead32(base, g_selectScreen + 148);
    const uint32_t player = players ? GRead32(base, players + (slot < 2 ? 48 : 56)) : 0;
    if (!player) return nullptr;
    const uint32_t record = GRead32(base, player + 348 + 4 * (slot & 1));
    const Fighter* f = ByRecord(record);
    uint32_t id = ~0u;
    // before its pick a member shows the cursor's fighter: the first member, or the second once the first is picked
    // (the first's record is set: below kTitleRecords or an added one; 139 = none)
    const uint32_t first = GRead32(base, player + 348);
    const bool choosing = (slot & 1) == 0 || first < kTitleRecords || ByRecord(first);
    if (!f && choosing && record >= kTitleRecords)
    {
        Call(ctx, base, __imp__sub_8227AE48, { player });
        id = ctx.r3.u32;
        f = ById(id);
    }
    static uint32_t logged = 0;
    if (Traced() && logged++ < 60)
        std::fprintf(stderr, "[added] portrait slot %u: record %u, cursor id %d -> %s\n", slot, record, int(id),
                     f ? f->name : "not added");
    return f;
}

extern "C" PPC_FUNC(__imp__sub_8262B2D0);
bool SecondAliased(uint8_t* base, uint32_t player);
PPC_FUNC(sub_8262B2D0)
{
    const uint32_t lister = ctx.r3.u32, row = ctx.r4.u32, slot = ctx.r5.u32;
    uint32_t at = 0, theirs = 0;
    if (On() && g_lister == lister && row == kAliasRow && (slot & 1) && slot < 4 && g_selectScreen)
    {
        const uint32_t players = GRead32(base, g_selectScreen + 148);
        const uint32_t player = players ? GRead32(base, players + (slot < 2 ? 48 : 56)) : 0;
        if (player && SecondAliased(base, player))
        {
            const Fighter* f = ByRecord(GRead32(base, player + 352));
            const uint32_t first = GRead32(base, lister + (slot < 2 ? 4 : 24));
            const uint32_t frame = f ? f->frames[slot < 2 ? 0 : 1] : GRead32(base, first + 4 * kDonorUiRow);
            if (frame)
            {
                at = first + 4 * row;
                theirs = GRead32(base, at);
                GWrite32(base, at, frame);
            }
        }
    }
    else if (On() && g_lister == lister && row == kDonorUiRow && slot < 4)
    {
        const PPCContext saved = ctx;
        const Fighter* f = SlotFighter(ctx, base, slot);
        ctx = saved;
        if (f && f->frames[slot < 2 ? 0 : 1])
        {
            const uint32_t first = GRead32(base, lister + (slot < 2 ? 4 : 24));
            at = first + 4 * row;
            theirs = GRead32(base, at);
            GWrite32(base, at, f->frames[slot < 2 ? 0 : 1]);
        }
    }
    __imp__sub_8262B2D0(ctx, base);
    if (at) GWrite32(base, at, theirs);
}

// The profile's per-fighter records (tk::profile::PartsCS::EachFighterInfoCS, Array<, 63>, 76 bytes each at
// profile +9216): sub_82659F48 (profile r3) updates the team members' records after a match, by each member's id
// byte (profile +640 + member * 4288). An added id indexed past the array (an ignored assert) and overwrote the
// profile data after it, and the next Arcade load after a continue never finished. While it runs, an added
// fighter's byte is Marduk's id: its results go to Marduk's record (as the other per-fighter save entry, sub_825550C8).
extern "C" PPC_FUNC(__imp__sub_82659F48);
PPC_FUNC(sub_82659F48)
{
    const uint32_t profile = ctx.r3.u32;
    uint8_t lent[2] = {};
    for (uint32_t k = 0; k < 2; ++k)
        if (profile && ById(base[profile + 640 + 4288 * k]))
        {
            lent[k] = base[profile + 640 + 4288 * k];
            base[profile + 640 + 4288 * k] = uint8_t(kDonorId);
        }
    __imp__sub_82659F48(ctx, base);
    for (uint32_t k = 0; k < 2; ++k)
        if (lent[k]) base[profile + 640 + 4288 * k] = lent[k];
    if (lent[0] || lent[1]) std::fprintf(stderr, "[added] profile %08X: fighter record as Marduk's\n", profile);
}

// The other accessors of the same per-fighter tables (count at *(table + 68) + 12; an index past it is the title's
// deliberate store to address 0) used when the save data is updated after a match, as sub_82584ED0: an added id is
// Marduk's there. Their failed checks were the null writes after a lost Arcade match, after which the next match's
// load (on continue) never finished.
namespace {
void AddedTableIndex(uint8_t* base, uint32_t table, PPCRegister& index, uint32_t lr, const char* fn)
{
    if (Traced())
    {
        static std::set<std::tuple<std::string, uint32_t, uint32_t>> seen;
        if (seen.size() < 300 && seen.emplace(fn, index.u32, lr).second)
            std::fprintf(stderr, "[added] table %s [%u], lr %08X\n", fn, index.u32, lr);
    }
    if (!(ById(index.u32) && table)) return;
    const uint32_t info = GRead32(base, table + 68);
    if (info && index.u32 < GRead32(base, info + 12)) return;
    static uint32_t logged = 0;
    if (logged++ < 20) std::fprintf(stderr, "[added] %s table %08X [%u] -> Marduk's, lr %08X\n", fn, table, index.u32, lr);
    index.u64 = kDonorId;
}
}
extern "C" PPC_FUNC(__imp__sub_82584E88);
PPC_FUNC(sub_82584E88)                      // (table r3, index r4): the entry, asserted set
{
    AddedTableIndex(base, ctx.r3.u32, ctx.r4, uint32_t(ctx.lr), "82584E88");
    __imp__sub_82584E88(ctx, base);
}
extern "C" PPC_FUNC(__imp__sub_82585230);
PPC_FUNC(sub_82585230)                      // (table r3, index r4, ...)
{
    AddedTableIndex(base, ctx.r3.u32, ctx.r4, uint32_t(ctx.lr), "82585230");
    __imp__sub_82585230(ctx, base);
}
extern "C" PPC_FUNC(__imp__sub_82585590);
PPC_FUNC(sub_82585590)                      // (table r3, ..., index r7, ...)
{
    AddedTableIndex(base, ctx.r3.u32, ctx.r7, uint32_t(ctx.lr), "82585590");
    __imp__sub_82585590(ctx, base);
}

// A player's body collision (sub_822FB4F8: player r3) takes a per-fighter pointer by id from two 64-entry tables
// (0x82DD0A68, and 0x82DD0B68 in some down states), read without a bound: Rick's 64 got the second table's first
// entry, and a downed Rick could not be hit (found 2026-10-25 by bisecting the functions that read player +84;
// Rick's files under Marduk's id 17 were hit). While it runs, an added fighter's id is Marduk's.
extern "C" PPC_FUNC(__imp__sub_822FB4F8);
PPC_FUNC(sub_822FB4F8)
{
    const uint32_t player = ctx.r3.u32;
    const uint32_t id = player ? GRead32(base, player + 84) : 0;
    const bool lend = player && ById(id);
    if (lend) GWrite32(base, player + 84, kDonorId);
    __imp__sub_822FB4F8(ctx, base);
    if (lend) GWrite32(base, player + 84, id);
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
            std::fprintf(stderr, "[added] grid cell (grids %08X mode %u, cell %d) lr %08X\n", ctx.r3.u32, mode,
                         int32_t(ctx.r4.u32), lr);
    }
    __imp__sub_8227A0D8(ctx, base);
}

// TTT2_RICK_TRACE: the 2D screens' sprite label jumps (sub_826278E0: layout r3, sprite name r4, label r5, both
// MSVC strings: the text inline under 16 characters of capacity, else at +0), each distinct one once.
extern "C" PPC_FUNC(__imp__sub_826278E0);
const Fighter* MemberFighter(PPCContext& ctx, uint8_t* base, uint32_t player, uint32_t member);
bool SecondAliased(uint8_t* base, uint32_t player);
extern const char* g_labelFrom;
extern const char* g_labelTo;
uint32_t g_selectUpdateScreen = 0;
PPC_FUNC(sub_826278E0)
{
    // On the select screen, a member's sprites (chara_face_yoko_main_p1, p1_chara_waku_sub, ...) are that member's: the
    // label renaming (sub_82B62BE8) goes by its fighter, not by whoever was asked about last (the update asks about
    // both members, then jumps both members' labels).
    const Fighter* asked = g_asked;
    bool scoped = false;
    if (On() && g.ready && g_selectUpdateScreen && ctx.r3.u32 == g_selectUpdateScreen)
    {
        const uint32_t s = ctx.r4.u32, at = GRead32(base, s + 20) >= 16 ? GRead32(base, s) : s;
        const char* name = reinterpret_cast<const char*>(base + at);
        const size_t n = strnlen(name, 100);
        const std::string sprite(name, n);
        const int member = sprite.find("_main") != std::string::npos ? 0 : sprite.find("_sub") != std::string::npos ? 1 : -1;
        const int player = sprite.find("p1") != std::string::npos ? 0 : sprite.find("p2") != std::string::npos ? 1 : -1;
        const uint32_t players = GRead32(base, g_selectUpdateScreen + 148);
        const uint32_t obj = member >= 0 && player >= 0 && players ? GRead32(base, players + (player ? 56 : 48)) : 0;
        if (obj)
        {
            const PPCContext saved = ctx;
            const Fighter* f = MemberFighter(ctx, base, obj, uint32_t(member));
            ctx = saved;
            g_asked = f;
            if (member == 1 && SecondAliased(base, obj))
            {
                g_labelFrom = "ste";
                g_labelTo = f ? f->code : "mar";
            }
            scoped = true;
        }
    }
    if (Traced())
    {
        auto text = [&](uint32_t s) {
            const uint32_t at = GRead32(base, s + 20) >= 16 ? GRead32(base, s) : s;
            return std::string(reinterpret_cast<const char*>(base + at), strnlen(reinterpret_cast<const char*>(base + at), 100));
        };
        static std::set<std::tuple<std::string, std::string, uint32_t>> seen;
        const std::string sprite = text(ctx.r4.u32), label = text(ctx.r5.u32);
        if (seen.size() < 400 && seen.emplace(sprite, label, uint32_t(ctx.lr)).second)
            std::fprintf(stderr, "[added] sprite %s -> label %s (asked %s), lr %08X\n", sprite.c_str(), label.c_str(),
                         g_asked ? g_asked->name : "-", uint32_t(ctx.lr));
    }
    __imp__sub_826278E0(ctx, base);
    if (scoped) { g_asked = asked; g_labelFrom = g_labelTo = nullptr; }
}

// Whether a select screen player's second member answers kAliasRow (both picked, the two different fighters of
// Rick, Jennifer and Marduk)
bool SecondAliased(uint8_t* base, uint32_t player)
{
    if (GRead32(base, player + 340) < 2) return false;
    const int a = RecordKey(GRead32(base, player + 348)), b = RecordKey(GRead32(base, player + 352));
    return a != -3 && b != -3 && a != b;
}

// A select screen player object's member (0, 1): its picked record, or before its pick the cursor's fighter (the
// first member, or the second once the first is picked); nullptr when not an added fighter.
const Fighter* MemberFighter(PPCContext& ctx, uint8_t* base, uint32_t player, uint32_t member)
{
    const uint32_t record = GRead32(base, player + 348 + 4 * member);
    if (record < kTitleRecords || ByRecord(record)) return ByRecord(record);
    const uint32_t picked = GRead32(base, player + 340);
    if (picked != member) return nullptr;
    Call(ctx, base, __imp__sub_8227AE48, { player });
    return ById(ctx.r3.u32);
}

// The VS screen (sub_826353D8) shows a side's second member's panel unless the side is solo, which sub_82634870
// (screen r3, side r4) decides by its two members' records (sub_822813D8(set-up, side) and (set-up, side + 2))
// having the same UI row: an added fighter has Marduk's row, so a team of Marduk and an added fighter, or of two
// added ones, showed one panel. It is solo only when the members are the same fighter.
extern "C" PPC_FUNC(__imp__sub_82634870);
extern "C" PPC_FUNC(__imp__sub_825B7370);
extern "C" PPC_FUNC(__imp__sub_822813D8);
PPC_FUNC(sub_82634870)
{
    const uint32_t screen = ctx.r3.u32, side = ctx.r4.u32 & 1;
    __imp__sub_82634870(ctx, base);
    if (!(ctx.r3.u32 && On() && g.ready)) return;
    const uint32_t result = ctx.r3.u32;
    Call(ctx, base, __imp__sub_825B7370, { screen });
    const uint32_t setup = ctx.r3.u32;
    Call(ctx, base, __imp__sub_822813D8, { setup, side });
    const uint32_t first = ctx.r3.u32;
    Call(ctx, base, __imp__sub_822813D8, { setup, side + 2 });
    const uint32_t second = ctx.r3.u32;
    ctx.r3.u64 = result;
    if (ByRecord(first) != ByRecord(second))
    {
        ctx.r3.u64 = 0;
        if (Traced())
            std::fprintf(stderr, "[added] side %u: records %u and %u, a tag team\n", side, first, second);
    }
}

// TTT2_RICK_TRACE: the select screen's big portraits (sub_826409E0: screen r3, slot r4, row r5) and its sprites'
// visibility (sub_826277B0: screen r3, sprite name r4 (MSVC string), shown r5), each distinct one once
extern "C" PPC_FUNC(__imp__sub_826277B0);
namespace {
std::string GuestString(uint8_t* base, uint32_t s)
{
    const uint32_t at = GRead32(base, s + 20) >= 16 ? GRead32(base, s) : s;
    return std::string(reinterpret_cast<const char*>(base + at), strnlen(reinterpret_cast<const char*>(base + at), 100));
}
}
PPC_FUNC(sub_826277B0)
{
    if (Traced())
    {
        static std::set<std::tuple<std::string, uint32_t, uint32_t>> seen;
        const std::string sprite = GuestString(base, ctx.r4.u32);
        if (seen.size() < 400 && seen.emplace(sprite, ctx.r5.u32 & 0xFF, uint32_t(ctx.lr)).second)
            std::fprintf(stderr, "[added] sprite %s shown %u, lr %08X\n", sprite.c_str(), ctx.r5.u32 & 0xFF,
                         uint32_t(ctx.lr));
    }
    __imp__sub_826277B0(ctx, base);
}

// The select screen's update (sub_82643A08: screen r3) shows each player's fighters by UI row, and redraws a slot only
// when its row changes: rows it last showed at screen + 4 * (43 + player) (the main face), (45 + player) (the second
// member's face) and (47 + player) (the big portraits; a change starts a short countdown, then sub_826409E0 shows the
// slot). An added fighter has Marduk's row, so moving the cursor from Rick to Jennifer (or between either and
// Marduk) kept the last one's pictures, and once both members were picked the second one's big portrait, hidden at the
// pick, never came back (the user's report: Rick, then Jennifer, in tag). Whenever whom a player shows changes (the
// cursor's fighter, the members' records) and an added fighter is or was among them, those rows are forgotten (-1),
// so the screen redraws them as for any other change, and the per-slot hooks above give each slot its own fighter.
extern "C" PPC_FUNC(__imp__sub_826277B0);
extern "C" PPC_FUNC(__imp__sub_826278E0);
extern uint32_t g_selectUpdateScreen;
PPC_FUNC(sub_8228CBD8);          // std::string(this, char*)
PPC_FUNC(sub_822864E8);          // ~std::string(this)
namespace {
// The update hides or skips a player's second member while both members have the same UI row (it takes them for one
// fighter): Rick, Jennifer and Marduk all have Marduk's row 18, so with two of them in a team the second member's big
// portrait stayed the first's, or vanished once picked. After the update, such a second member (picked, or under the
// cursor once the first is picked) is drawn here as the update draws one: its big portrait (sub_826409E0: slot
// player * 2 + 1, row 18, which sub_8262B2D0 above gives the member's own frame), its frame label
// (p<n>_chara_waku_sub -> p<n>_chara_waku_mar) and small face (chara_face_yoko_sub_p<n> -> chara_face_yoko_mar),
// renamed to its code by sub_82B62BE8; once per change (g_drawn).
int g_drawn[2] = { -99, -99 };               // the second member drawn here (fighter key * 4 + members picked)
int FighterKey(uint32_t record, uint32_t id, bool byRecord)
{
    if (byRecord) { if (const Fighter* f = ByRecord(record)) return int(f - kFighters);
                    return record == kDonorRecord0 || record == kDonorRecord0 + 1 ? -1 : -3; }
    if (const Fighter* f = ById(id)) return int(f - kFighters);
    return id == kDonorId ? -1 : -3;
}
uint32_t GuestStr(PPCContext& ctx, uint8_t* base, uint32_t obj, uint32_t text, const char* value)
{
    std::memcpy(base + text, value, std::strlen(value) + 1);
    Call(ctx, base, sub_8228CBD8, { obj, text });
    return obj;
}
void SelectSecondMembers(PPCContext& ctx, uint8_t* base, uint32_t screen)
{
    const uint32_t players = On() && g.ready && screen ? GRead32(base, screen + 148) : 0;
    for (uint32_t p = 0; players && p < 2; ++p)
    {
        const uint32_t player = GRead32(base, players + (p ? 56 : 48));
        if (!player) continue;
        const uint32_t size = GRead32(base, player + 336), picked = GRead32(base, player + 340);
        int first = -3, second = -3;
        if (size == 2 && picked == 1)               // once both are picked, kAliasRow does it
        {
            first = FighterKey(GRead32(base, player + 348), 0, true);
            Call(ctx, base, __imp__sub_8227AE48, { player });
            second = FighterKey(0, ctx.r3.u32, false);
        }
        const bool ours = first != -3 && second != -3 && first != second;
        if (!ours) { g_drawn[p] = -99; continue; }
        const int key = second * 4 + int(picked);
        if (g_drawn[p] == key) continue;
        g_drawn[p] = key;
        const Fighter* asked = g_asked;
        g_asked = second >= 0 ? &kFighters[second] : nullptr;
        Call(ctx, base, __imp__sub_826409E0, { screen, 2 * p + 1, kDonorUiRow });
        const uint32_t s = g.scratch + 640, t = g.scratch + 768;   // 3 string objects (32 bytes), their texts
        char sprite[40], label[40];
        std::snprintf(sprite, sizeof(sprite), "p%u_chara_waku_sub", p + 1);
        std::snprintf(label, sizeof(label), "p%u_chara_waku_mar", p + 1);
        GuestStr(ctx, base, s, t, sprite);
        GuestStr(ctx, base, s + 32, t + 48, label);
        Call(ctx, base, __imp__sub_826277B0, { screen, s, 1 });
        Call(ctx, base, __imp__sub_826278E0, { screen, s, s + 32 });
        Call(ctx, base, sub_822864E8, { s });
        Call(ctx, base, sub_822864E8, { s + 32 });
        std::snprintf(sprite, sizeof(sprite), "chara_face_yoko_sub_p%u", p + 1);
        GuestStr(ctx, base, s, t, sprite);
        GuestStr(ctx, base, s + 32, t + 48, "chara_face_yoko_mar");
        Call(ctx, base, __imp__sub_826277B0, { screen, s, 1 });
        Call(ctx, base, __imp__sub_826278E0, { screen, s, s + 32 });
        Call(ctx, base, sub_822864E8, { s });
        Call(ctx, base, sub_822864E8, { s + 32 });
        g_asked = asked;
        if (Traced())
            std::fprintf(stderr, "[added] select player %u: second member %d drawn (first %d)\n", p, second, first);
    }
}
struct Shown { uint32_t cursor = ~0u, first = ~0u, second = ~0u; };
Shown g_shown[2];
bool Involves(const Shown& s) { return ById(s.cursor) || ByRecord(s.first) || ByRecord(s.second); }
}
extern "C" PPC_FUNC(__imp__sub_82643A08);
PPC_FUNC(sub_82643A08)
{
    const uint32_t screen = ctx.r3.u32;
    const uint32_t players = On() && g.ready && screen ? GRead32(base, screen + 148) : 0;
    for (uint32_t p = 0; players && p < 2; ++p)
    {
        const uint32_t player = GRead32(base, players + (p ? 56 : 48));
        if (!player) continue;
        Shown now;
        now.first = GRead32(base, player + 348);
        now.second = GRead32(base, player + 352);
        Call(ctx, base, __imp__sub_8227AE48, { player });
        now.cursor = ctx.r3.u32;
        ctx.r3.u64 = screen;
        Shown& was = g_shown[p];
        if ((now.cursor != was.cursor || now.first != was.first || now.second != was.second) &&
            (Involves(now) || Involves(was)))
        {
            for (uint32_t k : { 43u, 45u, 47u }) GWrite32(base, screen + 4 * (k + p), ~0u);
            if (Traced())
                std::fprintf(stderr, "[added] select player %u: cursor %d, records %d/%d: rows redrawn\n", p,
                             int(now.cursor), int(now.first), int(now.second));
        }
        was = now;
    }
    g_selectUpdateScreen = screen;
    g_inSelect = On() && g.ready;
    g_firstKey = -3;
    __imp__sub_82643A08(ctx, base);
    g_inSelect = false;
    SelectSecondMembers(ctx, base, screen);
    g_selectUpdateScreen = 0;
}


// Customize (its grid: ttt2rick.convert.menus, RICK_CUSTOMIZE=1). The mode's per-fighter data are by internal id, in
// tables and maps that know ids 0-62; an added fighter is customized as Marduk (his items: ttt2rick.convert.slot
// item_database gives Rick Marduk's whole item database), while the fighter shown is the added one (its record).
// Each of these, given 64, asked for a key past the end of its table and waited for it for good.
namespace {
bool CustomizedAsDonor(uint32_t id) { return ById(id) != nullptr; }
}

extern "C" PPC_FUNC(__imp__sub_8272A5F0);
PPC_FUNC(sub_8272A5F0)                      // the costume panel's loader (this, slot r4, fighter id r5 < 128)
{
    if (CustomizedAsDonor(ctx.r5.u32)) ctx.r5.u64 = kDonorId;
    __imp__sub_8272A5F0(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_8227A078);
PPC_FUNC(sub_8227A078)                      // id -> its costume panel pictures' key (63-entry table 0x8200C7D0; the
{                                           // panel's IsBusy native waits until that file is loaded): an added
    if (const Fighter* f = ById(ctx.r3.u32))   // fighter's own, <code>/costume_panel.nut (ttt2rick.convert.panel)
    {
        const std::string name = std::string(f->code) + "/costume_panel.nut";
        ctx.r3.u64 = Crc(name.c_str());
        return;
    }
    __imp__sub_8227A078(ctx, base);
}

// The select screen's costume panel (X changes the costume) reads the same 63-key table inline, by id (r4): for an
// added fighter, the entry its id reads (past the table's end) holds its own key while the function runs.
namespace {
void WithPanelKey(PPCContext& ctx, uint8_t* base, void (*fn)(PPCContext&, uint8_t*))
{
    const Fighter* f = ById(ctx.r4.u32);
    if (!f) { fn(ctx, base); return; }
    const uint32_t entry = 0x8200C7D0 + 4 * f->id, was = GRead32(base, entry);
    GWrite32(base, entry, Crc((std::string(f->code) + "/costume_panel.nut").c_str()));
    fn(ctx, base);
    GWrite32(base, entry, was);
}
}

extern "C" PPC_FUNC(__imp__sub_8227DB70);
PPC_FUNC(sub_8227DB70)                      // (this, id r4): requests the panel's pictures file
{
    WithPanelKey(ctx, base, __imp__sub_8227DB70);
}

extern "C" PPC_FUNC(__imp__sub_8227ED80);
PPC_FUNC(sub_8227ED80)                      // (this, id r4): builds the panel once that file is loaded (r3 0 until
{                                           // then; with the key past the table's end it never was)
    WithPanelKey(ctx, base, __imp__sub_8227ED80);
}

extern "C" PPC_FUNC(__imp__sub_82717200);
PPC_FUNC(sub_82717200)                      // (this, id r4): the fighter's Customize item list (data051), by a
{                                           // 63-entry key table
    if (CustomizedAsDonor(ctx.r4.u32)) ctx.r4.u64 = kDonorId;
    __imp__sub_82717200(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_82728B28);
PPC_FUNC(sub_82728B28)                      // (this, id r4): starts Customize's fighter data for the id (this +60):
{                                           // its item maps are keyed by it, and its BXML (data052, sub_82725088)
    if (CustomizedAsDonor(ctx.r4.u32))      // comes from a 63-entry key table by it
    {
        std::fprintf(stderr, "[added] Customize: id %u as Marduk's\n", ctx.r4.u32);
        ctx.r4.u64 = kDonorId;
    }
    __imp__sub_82728B28(ctx, base);
}

extern "C" PPC_FUNC(__imp__sub_82413AC0);
PPC_FUNC(sub_82413AC0)                      // (this, id r4, out list r5): the fighter's preset costumes (Customize's
{                                           // A/B panels; a table by id at 0x8205DBD0, nothing above 58): Marduk's
    if (CustomizedAsDonor(ctx.r4.u32)) ctx.r4.u64 = kDonorId;
    __imp__sub_82413AC0(ctx, base);
}
