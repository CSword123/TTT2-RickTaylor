// The mod DLL's stand-in for SIMDe (which the recomp's ppc_context.h includes): the SIMDe names that header
// uses, as the native SSE / SSE4.1 intrinsics they wrap on x86-64 (written by hand from its list; the
// header's own helpers it defines itself). The DLL only needs the header's types; these keep it compiling.
#pragma once
#include <immintrin.h>

#define simde__m128 __m128
#define simde__m128i __m128i
#define simde_mm_add_epi32 _mm_add_epi32
#define simde_mm_and_si128 _mm_and_si128
#define simde_mm_andnot_si128 _mm_andnot_si128
#define simde_mm_avg_epu16 _mm_avg_epu16
#define simde_mm_avg_epu8 _mm_avg_epu8
#define simde_mm_blendv_epi8 _mm_blendv_epi8
#define simde_mm_blendv_ps _mm_blendv_ps
#define simde_mm_castps_si128 _mm_castps_si128
#define simde_mm_castsi128_ps _mm_castsi128_ps
#define simde_mm_cmpeq_epi32 _mm_cmpeq_epi32
#define simde_mm_cmpge_ps _mm_cmpge_ps
#define simde_mm_cmpgt_epi16 _mm_cmpgt_epi16
#define simde_mm_cmpgt_epi32 _mm_cmpgt_epi32
#define simde_mm_cmpgt_epi8 _mm_cmpgt_epi8
#define simde_mm_cmpunord_ps _mm_cmpunord_ps
#define simde_mm_cvtepi32_ps _mm_cvtepi32_ps
#define simde_mm_cvttps_epi32 _mm_cvttps_epi32
#define simde_mm_extract_epi8 _mm_extract_epi8
#define simde_mm_getcsr _mm_getcsr
#define simde_mm_insert_ps _mm_insert_ps
#define simde_mm_max_ps _mm_max_ps
#define simde_mm_min_epu32 _mm_min_epu32
#define simde_mm_movemask_epi8 _mm_movemask_epi8
#define simde_mm_movemask_ps _mm_movemask_ps
#define simde_mm_or_ps _mm_or_ps
#define simde_mm_or_si128 _mm_or_si128
#define simde_mm_set1_epi16 _mm_set1_epi16
#define simde_mm_set1_epi32 _mm_set1_epi32
#define simde_mm_set1_epi8 _mm_set1_epi8
#define simde_mm_setcsr _mm_setcsr
#define simde_mm_setzero_ps _mm_setzero_ps
#define simde_mm_shuffle_epi8 _mm_shuffle_epi8
#define simde_mm_slli_epi32 _mm_slli_epi32
#define simde_mm_slli_epi64 _mm_slli_epi64
#define simde_mm_slli_si128 _mm_slli_si128
#define simde_mm_srai_epi32 _mm_srai_epi32
#define simde_mm_srl_epi64 _mm_srl_epi64
#define simde_mm_srli_epi32 _mm_srli_epi32
#define simde_mm_srli_epi64 _mm_srli_epi64
#define simde_mm_srli_si128 _mm_srli_si128
#define simde_mm_sub_epi8 _mm_sub_epi8
#define simde_mm_sub_ps _mm_sub_ps
#define simde_mm_xor_si128 _mm_xor_si128
#define SIMDE_MM_FLUSH_ZERO_MASK _MM_FLUSH_ZERO_MASK
#define SIMDE_MM_ROUND_DOWN _MM_ROUND_DOWN
#define SIMDE_MM_ROUND_MASK _MM_ROUND_MASK
#define SIMDE_MM_ROUND_NEAREST _MM_ROUND_NEAREST
#define SIMDE_MM_ROUND_TOWARD_ZERO _MM_ROUND_TOWARD_ZERO
#define SIMDE_MM_ROUND_UP _MM_ROUND_UP
