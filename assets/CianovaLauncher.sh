#!/bin/bash

#Exportar LIBS y BINS
export PATH="/bin:$PATH"
export MCPELAUNCHER_DATA_DIR="/lib"

exec ./CianovaLauncherMCPE "$@"
