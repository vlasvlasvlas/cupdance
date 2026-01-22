#!/bin/bash

echo "======================================"
echo "   CUPDANCE SOTA INSTRUMENT v2.0"
echo "======================================"
echo ""

# 1. Check Virtual Env
if [ ! -d "venv" ]; then
    echo "[Launcher] Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 2. Main Launch (Wizard runs automatically if needed)
echo ""
echo "[Launcher] Iniciando Sistema..."
echo "  - El wizard de configuracion se abre automaticamente"
echo "  - Todas las instrucciones estan en pantalla"
echo ""

python main.py

echo ""
echo "[Launcher] Shutdown complete."
