#!/bin/bash
# Recompila gplaydl + gplayver desde upstream con parches Cianova.
# Uso: bash scripts/build/build_gplaydl.sh [ruta-clone-opcional]
#
# Aplica dos parches a Google-Play-API:
#  1. Elimina printf("...%s", proto.DebugString()) que crashean con respuestas
#     TOC actuales de Google bajo libprotobuf 32 (unknown fields).
#  2. download_component chequea downloadauthcookie_size() antes de Get(0) y
#     emite "error: delivery status=N" parseable por el launcher.
#
# Resultado: bin/gplaydl, bin/gplayver Release listos para distribución.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST_BIN="${PROJECT_ROOT}/bin"
REPO="${1:-/tmp/mcpelauncher-ui-manifest/google-play-api}"

if [ ! -d "$REPO" ]; then
    echo "Cloning Google-Play-API..."
    mkdir -p "$(dirname "$REPO")"
    git clone --depth 1 https://github.com/minecraft-linux/Google-Play-API "$REPO"
fi

# Deps build (Debian/Ubuntu). Adapt for other distros.
if command -v apt >/dev/null; then
    if ! dpkg -s libprotobuf-dev >/dev/null 2>&1; then
        echo "== Installing build deps (sudo required) =="
        sudo apt update
        sudo apt install -y build-essential cmake pkg-config \
            libcurl4-openssl-dev libssl-dev zlib1g-dev \
            libprotobuf-dev protobuf-compiler libabsl-dev
    fi
fi

# Apply patches if not already applied
cd "$REPO"
if grep -q 'printf("api response body = %s' lib/playapi/api.cpp 2>/dev/null; then
    echo "== Applying DebugString crash patch =="
    sed -i 's|printf("api response body = %s\\n", ret.DebugString().c_str());|/* removed: DebugString crashes on unknown fields */|' lib/playapi/api.cpp
    sed -i 's|printf("Upload Device Config: %s\\n", req.DebugString().c_str());|/* removed */|' lib/playapi/api.cpp
    sed -i 's|printf("Checkin data: %s\\n", req.DebugString().c_str());|/* removed */|' lib/playapi/checkin.cpp
    sed -i 's|printf("Checkin response: %s\\n", resp.DebugString().c_str());|/* removed */|' lib/playapi/checkin.cpp
fi

if ! grep -q "downloadauthcookie_size" src/gplaydl.cpp 2>/dev/null; then
    echo "== Applying delivery diagnostic patch =="
    python3 - <<'PY'
import re, pathlib
p = pathlib.Path("src/gplaydl.cpp")
s = p.read_text()
old = ('        auto resp = api.delivery(opt_app, opt_app_version, std::string())->call();\n'
       '        auto dd = resp.payload().deliveryresponse().appdeliverydata();\n\n'
       '        download_component(dd, dd.downloadauthcookie(0), "");\n\n'
       '        for(auto && data : dd.splitdeliverydata()) {\n'
       '            download_component(data, dd.downloadauthcookie(0), data.id());\n'
       '        }')
new = ('        auto resp = api.delivery(opt_app, opt_app_version, std::string())->call();\n'
       '        auto& delresp = resp.payload().deliveryresponse();\n'
       '        if (delresp.has_status() && delresp.status() != 1) {\n'
       '            std::cerr << "error: delivery status=" << delresp.status();\n'
       '            if (delresp.has_appdeliverydata())\n'
       '                std::cerr << " (appdeliverydata present)";\n'
       '            std::cerr << ". The Google account likely does not own this app, "\n'
       '                      << "or library context is missing." << std::endl;\n'
       '            exit(1);\n'
       '        }\n'
       '        auto dd = delresp.appdeliverydata();\n'
       '        if (dd.downloadauthcookie_size() == 0) {\n'
       '            std::cerr << "error: no downloadauthcookie returned. "\n'
       '                      << "Account does not own \'" << opt_app << "\' on Google Play, "\n'
       '                      << "OR ownership replication is required. delivery_status="\n'
       '                      << (delresp.has_status() ? std::to_string(delresp.status()) : "absent")\n'
       '                      << ", downloadurl=" << (dd.has_downloadurl() ? dd.downloadurl() : "(none)")\n'
       '                      << std::endl;\n'
       '            exit(1);\n'
       '        }\n\n'
       '        download_component(dd, dd.downloadauthcookie(0), "");\n\n'
       '        for(auto && data : dd.splitdeliverydata()) {\n'
       '            download_component(data, dd.downloadauthcookie(0), data.id());\n'
       '        }')
if old not in s:
    raise SystemExit("Upstream src/gplaydl.cpp shape changed; patch by hand.")
p.write_text(s.replace(old, new))
PY
fi

# Build
echo "== cmake (Debug to keep useful prints, with patches removing DebugString) =="
rm -rf build
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..

echo "== make =="
make -j"$(nproc)" gplaydl gplayver

# Install
mkdir -p "$DEST_BIN"
for b in gplaydl gplayver; do
    if [ -x "./$b" ]; then
        cp -v "$DEST_BIN/$b" "$DEST_BIN/$b.prev" 2>/dev/null || true
        cp -v "./$b" "$DEST_BIN/$b"
    fi
done

echo ""
echo "Done. Patched binaries copied to $DEST_BIN/"
echo "Backup of previous version: $DEST_BIN/gplaydl.prev"
