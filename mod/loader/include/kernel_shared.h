// The mod DLL's stand-in for the recomp's kernel/kernel_shared.h: the guest memory helpers Rick's hooks use (the same
// as the recomp's own).
#pragma once
#include "ppc_recomp_shared.h"
#include <cstdint>

inline uint32_t GRead32(uint8_t* base, uint32_t ga)  { return __builtin_bswap32(*reinterpret_cast<uint32_t*>(base + ga)); }
inline uint16_t GRead16(uint8_t* base, uint32_t ga)  { return __builtin_bswap16(*reinterpret_cast<uint16_t*>(base + ga)); }
inline uint8_t  GRead8 (uint8_t* base, uint32_t ga)  { return *(base + ga); }
inline void GWrite32(uint8_t* base, uint32_t ga, uint32_t v) { if (ga) *reinterpret_cast<uint32_t*>(base + ga) = __builtin_bswap32(v); }
inline void GWrite16(uint8_t* base, uint32_t ga, uint16_t v) { if (ga) *reinterpret_cast<uint16_t*>(base + ga) = __builtin_bswap16(v); }
inline void GWrite8 (uint8_t* base, uint32_t ga, uint8_t  v) { if (ga) *(base + ga) = v; }
inline uint32_t GuestAddr(uint8_t* base, void* host) { return static_cast<uint32_t>(static_cast<uint8_t*>(host) - base); }
