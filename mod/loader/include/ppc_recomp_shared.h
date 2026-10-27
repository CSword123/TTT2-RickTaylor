// The mod DLL's stand-in for the recomp's generated ppc_recomp_shared.h: the PPC context, and declarations of just
// the guest functions Rick's hooks name (guest_fns.gen.h, written by mod/loader/gen.py), whose host code the loader
// finds in the running recomp (loader.cpp).
#pragma once
#include "ppc_config.h"
#include "ppc_context.h"
#if __has_include("guest_fns.gen.h") && !defined(TTT2RICK_GEN_PASS)     // (gen.py's own pass reads the hooks alone)
#include "guest_fns.gen.h"
#endif
