// The added fighters' voices (TTT2-RickTaylor project; after Petexy's Wii U port, runtime/src/title/roster.cpp):
// Rick shouts and groans with Splatterhouse's grunts, from a sound bank of his own (se_Chr_ric.nus3bank, made by
// ttt2rick.convert.voice from Marduk's se_Chr_mar, the same tones in the same order). TTT2_RICK=1 turns it on.
//
// How the title voices a fighter (internal id):
// - its se_Chr bank (shouts, damage voices, KO screams) is the game bank id sub_825A55F8(id) gives (ids above 62:
//   -1, no bank); a match loads it with the other members' banks (sub_825A1E18) by the key sub_825A6010(bank id)
//   gives (a switch over 0..261; Marduk's bank 33 is se_Chr_mar's key);
// - a move's shout, a hit's groan: the n-th entry of a category in the fighter's voice list (sub_825A2DF8(id,
//   category, n); sub_825A2F08(id, category) counts them), whose +4 is a sound id; the run-time lists (built at
//   start-up from the static ones at 0x82DE86F8, by id) stop at id 62;
// - a sound id's entry in the sound table (sub_825A3318 gives it and its count, 8252) is {tone, game bank id, group,
//   flags}; sound ids 8253..8433 are remapped to others first (sub_825A3450), so new ones start above.
// An added fighter with a voice (kVoices) gets: a free game bank id whose key is its bank's, Marduk's voice list
// with its own sound ids, and those sound ids in an extended sound table (copies of Marduk's entries, its bank).
#include "kernel_shared.h"
#include "guest_heap.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iterator>

extern "C" PPC_FUNC(__imp__sub_825A55F8);   // id -> its se_Chr game bank id
extern "C" PPC_FUNC(__imp__sub_825A6010);   // game bank id -> its file's key
extern "C" PPC_FUNC(__imp__sub_825A2F08);   // (id, category) -> how many voice entries
extern "C" PPC_FUNC(__imp__sub_825A2DF8);   // (id, category, n) -> the entry
extern "C" PPC_FUNC(__imp__sub_825A3318);   // (&count) -> the sound table

namespace {
constexpr uint32_t kDonorId = 17;
constexpr uint32_t kVoiceLists = 0x82DE86F8;            // 63 x {entries, count, id}; an entry 16 B
constexpr uint32_t kSoundTable = 0x82DE8C28;            // 8252 x {tone, game bank id, group, flags}
constexpr uint32_t kTitleSounds = 8252;
constexpr uint32_t kFirstNewSound = 8434;               // past the ids sub_825A3450 remaps (8253..8433)

struct Voice
{
    uint32_t id;
    const char* bank;               // its se_Chr bank's file name
    uint32_t gameBank;              // a game bank id no title bank has (sub_825A6010's default case)
    // at run time
    uint32_t entries = 0, count = 0, firstSound = 0;
};

Voice kVoices[] = {
    { 64, "se_Chr_ric.nus3bank", 1 },
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

uint32_t Alloc(uint8_t* base, uint32_t size)
{
    void* p = g_virtualHeap.Alloc(size, 16);
    std::memset(p, 0, size);
    return uint32_t(static_cast<uint8_t*>(p) - base);
}

struct Tables
{
    bool ready = false;
    uint32_t sounds = 0, count = kTitleSounds;           // the extended sound table
} g;

// Each voice's list (Marduk's, its fighter and sound ids its own) and the sound table with their entries: Marduk's
// entries of those sounds with the voice's bank.
void Prepare(uint8_t* base)
{
    if (g.ready) return;
    g.ready = true;
    const uint32_t donorEntries = GRead32(base, kVoiceLists + 12 * kDonorId);
    const uint32_t donorCount = GRead32(base, kVoiceLists + 12 * kDonorId + 4);
    uint32_t next = kFirstNewSound;
    for (Voice& v : kVoices)
    {
        v.count = donorCount;
        v.entries = Alloc(base, 16 * donorCount);
        std::memcpy(base + v.entries, base + donorEntries, 16 * donorCount);
        v.firstSound = next;
        for (uint32_t j = 0; j < donorCount; ++j)
        {
            GWrite32(base, v.entries + 16 * j, v.id);
            GWrite32(base, v.entries + 16 * j + 4, next + j);
        }
        next += donorCount;
    }
    const uint32_t title = kSoundTable;
    g.count = next;
    g.sounds = Alloc(base, 16 * g.count);
    std::memcpy(base + g.sounds, base + title, 16 * kTitleSounds);
    for (const Voice& v : kVoices)
        for (uint32_t j = 0; j < v.count; ++j)
        {
            const uint32_t sid = GRead32(base, donorEntries + 16 * j + 4);
            const uint32_t to = g.sounds + 16 * (v.firstSound + j);
            std::memcpy(base + to, base + title + 16 * sid, 16);
            GWrite32(base, to + 4, v.gameBank);
        }
    std::fprintf(stderr, "[voice] sound table %08X: %u entries (the title's %u), %u voices\n", g.sounds, g.count,
                 kTitleSounds, uint32_t(std::size(kVoices)));
}

Voice* ById(uint32_t id)
{
    if (!On()) return nullptr;
    for (Voice& v : kVoices)
        if (v.id == id) return &v;
    return nullptr;
}
}

PPC_FUNC(sub_825A55F8)
{
    if (Voice* v = ById(ctx.r3.u32))
    {
        ctx.r3.u64 = v->gameBank;
        return;
    }
    __imp__sub_825A55F8(ctx, base);
}

PPC_FUNC(sub_825A6010)
{
    if (On())
        for (const Voice& v : kVoices)
            if (ctx.r3.u32 == v.gameBank)
            {
                ctx.r3.u64 = Crc(v.bank);
                std::fprintf(stderr, "[voice] game bank %u -> %s (%08X)\n", v.gameBank, v.bank, ctx.r3.u32);
                return;
            }
    __imp__sub_825A6010(ctx, base);
}

PPC_FUNC(sub_825A2F08)
{
    if (ById(ctx.r3.u32)) ctx.r3.u64 = kDonorId;
    __imp__sub_825A2F08(ctx, base);
}

PPC_FUNC(sub_825A2DF8)
{
    Voice* v = ById(ctx.r3.u32);
    if (!v)
    {
        __imp__sub_825A2DF8(ctx, base);
        return;
    }
    Prepare(base);
    ctx.r3.u64 = kDonorId;
    __imp__sub_825A2DF8(ctx, base);
    const uint32_t donorEntries = GRead32(base, kVoiceLists + 12 * kDonorId);
    const uint32_t e = ctx.r3.u32;
    if (e >= donorEntries && e < donorEntries + 16 * v->count) ctx.r3.u64 = v->entries + (e - donorEntries);
    static uint32_t logged = 0;
    if (logged++ < 40 && ctx.r3.u32)
        std::fprintf(stderr, "[voice] id %u: entry %08X, sound %u\n", v->id, ctx.r3.u32, GRead32(base, ctx.r3.u32 + 4));
}

PPC_FUNC(sub_825A3318)
{
    if (!On())
    {
        __imp__sub_825A3318(ctx, base);
        return;
    }
    Prepare(base);
    if (ctx.r3.u32) GWrite32(base, ctx.r3.u32, g.count);
    ctx.r3.u64 = g.sounds;
}
