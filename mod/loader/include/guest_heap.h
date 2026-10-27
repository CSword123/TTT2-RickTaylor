// The mod DLL's stand-in for the recomp's kernel/guest_heap.h: g_virtualHeap.Alloc, which the hooks use for their
// few guest buffers, takes them from the recomp's own guest heap through the game's kernel call ExAllocatePool
// (whose recomp implementation is that heap's Alloc(size, 16)): loader.cpp ModGuestAlloc.
#pragma once
#include <cstddef>

void* ModGuestAlloc(size_t size, size_t align);

struct ModGuestHeap
{
    void* Alloc(size_t size, size_t align) { return ModGuestAlloc(size, align); }
};
inline ModGuestHeap g_virtualHeap;
