// The added fighters' settings (TTT2-RickTaylor project): each is an environment variable, or else a line of
// ttt2rick.ini next to the game's exe (which the mod's installer writes, mod/install.py):
//
//   [ttt2rick]
//   rick = 1          ; TTT2_RICK: the added fighters at all
//   jennifer = 1      ; TTT2_JEN: Jennifer as well as Rick
//   blood = 0         ; TTT2_RICK_BLOOD: Splatterhouse's blood on Rick (his clothes, Mirror Rick's skin, portraits)
//
// An environment variable of the same name wins over the file (TTT2_RICK=0 turns the mod off for one run).
#pragma once
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

// TTT2_RICK when nothing says: off in a recomp built with the hooks (an exe that is also the stock game), on in the
// mod's loader DLL (mod/loader/build.sh defines TTT2RICK_MOD=1), which is there to load Rick
#ifndef TTT2RICK_MOD
#define TTT2RICK_MOD 0
#endif
constexpr bool kRickByDefault = TTT2RICK_MOD != 0;

namespace rick_settings {

// the variable's key in the file
inline const char* IniKey(const char* name)
{
    if (!std::strcmp(name, "TTT2_RICK")) return "rick";
    if (!std::strcmp(name, "TTT2_JEN")) return "jennifer";
    if (!std::strcmp(name, "TTT2_RICK_BLOOD")) return "blood";
    return nullptr;
}

// ttt2rick.ini's value of `key` (its first character), or 0 when the file or the line is missing
inline char FromIni(const char* key)
{
    char exe[MAX_PATH] = {};
    if (!GetModuleFileNameA(nullptr, exe, MAX_PATH)) return 0;
    std::string path(exe);
    path = path.substr(0, path.find_last_of("\\/") + 1) + "ttt2rick.ini";
    FILE* f = std::fopen(path.c_str(), "r");
    if (!f) return 0;
    char line[256], value = 0;
    while (!value && std::fgets(line, sizeof(line), f))
    {
        const char* p = line;
        while (*p == ' ' || *p == '\t') ++p;
        const size_t n = std::strlen(key);
        if (std::strncmp(p, key, n) != 0) continue;
        p += n;
        while (*p == ' ' || *p == '\t') ++p;
        if (*p++ != '=') continue;
        while (*p == ' ' || *p == '\t') ++p;
        if (*p && *p != ';' && *p != '\r' && *p != '\n') value = *p;
    }
    std::fclose(f);
    return value;
}

}   // namespace rick_settings

// TTT2_RICK, TTT2_JEN or TTT2_RICK_BLOOD: on ('1') or off, from the environment or ttt2rick.ini; `otherwise` when
// neither says
inline bool RickSetting(const char* name, bool otherwise)
{
    if (const char* e = std::getenv(name); e && *e) return *e == '1';
    const char* key = rick_settings::IniKey(name);
    const char v = key ? rick_settings::FromIni(key) : 0;
    return v ? v == '1' : otherwise;
}
