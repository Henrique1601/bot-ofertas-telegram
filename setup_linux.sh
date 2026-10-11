#!/usr/bin/env bash
# Script de instalação e configuração automática do Bot de Ofertas no Linux (Ubuntu/Debian)
set -e

echo "======================================================"
echo "🚀 Instalando dependências do Bot de Ofertas na VPS"
echo "======================================================"

# Atualiza pacotes do sistema
sudo apt-get update
sudo apt-get install -y curl ca-certificates git libnss3 libnspr4 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2

# Instala o gerenciador de pacotes uv se ainda não estiver instalado
if ! command -v uv &> /dev/null; then
    echo "📦 Instalando astral-sh/uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "📦 Sincronizando ambiente Python do bot..."
uv sync

echo "🌐 Instalando Chromium do Playwright..."
uv run python -m ofertas instalar-navegador || uv run playwright install --with-deps chromium

echo "======================================================"
echo "✅ Ambiente pronto!"
echo "Para testar a configuração, rode: uv run python -m ofertas check"
echo "Para iniciar o bot manualmente, rode: uv run python -m ofertas run"
echo "======================================================"
