#!/bin/sh
# Run a Windows program with Steam's Proton in this folder's own prefix (pfx/), outside Steam.
#   proton/run.sh <program.exe> [args...]      exit code is the program's
#   PROTON=/path/to/proton proton/run.sh ...    another Proton build (default: Proton 10.0)
# Arguments are passed as given: give Windows paths (Z:\home\...) to Windows programs; see winpath.
HERE=$(cd "$(dirname "$0")" && pwd)
STEAM="$HOME/.local/share/Steam"
export STEAM_COMPAT_DATA_PATH="$HERE/pfx"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM"
# Microsoft's d3dcompiler_47.dll next to the program, when there is one: Wine's own compiler (vkd3d-shader) rejects
# shaders TTT2-Recomp 0.2.0 translates (E5000/E5002/E5008), and their draws (the fighters' bodies) are skipped.
# winmm: the Rick mod's loader (mod/loader) when it is next to the program; Wine's own otherwise.
export WINEDLLOVERRIDES="d3dcompiler_47=n,b;winmm=n,b${WINEDLLOVERRIDES:+;$WINEDLLOVERRIDES}"
PROTON="${PROTON:-$STEAM/steamapps/common/Proton 10.0/proton}"
exec python3 "$PROTON" waitforexitandrun "$@"
