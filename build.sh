#!/bin/bash

echo "Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing dependencies..."
pip install PySide6 Pillow pyinstaller

echo "Dependencies installed."
echo "Building executable..."
# --collect-all customtkinter es necesario para incluir los temas y archivos json de la librería
# --add-data "icon.png:." incluye el icono dentro del ejecutable (en la raíz)
# --icon "icon.png" establece el icono del ejecutable (para el explorador de archivos)
./venv/bin/pyinstaller --noconfirm --onedir --clean CianovaLauncherMCPE.spec

echo "Build complete!"
echo "Executable is located at: dist/CianovaLauncherMCPE"
