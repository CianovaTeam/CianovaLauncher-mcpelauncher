#!/bin/bash
SELF_DIR="$(dirname "$(readlink -f "$0")")"

export PATH="${SELF_DIR}/bin:$PATH"
export LD_LIBRARY_PATH="${SELF_DIR}/_internal:${LD_LIBRARY_PATH}"
export MCPELAUNCHER_DATA_DIR="${SELF_DIR}/lib"
export QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox --ignore-gpu-blocklist"
export QT_QUICK_BACKEND="software"

exec "${SELF_DIR}/CianovaLauncherMCPE" "$@"
