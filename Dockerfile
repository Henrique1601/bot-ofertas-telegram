# Dockerfile para Bot de Ofertas Telegram
FROM python:3.12-slim

# Instala dependências de sistema necessárias para o Chromium / Playwright headless no Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Instala o uv para gerenciar o ambiente Python de forma ultrarrápida
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copia as definições de dependências
COPY pyproject.toml uv.lock ./

# Sincroniza as dependências do projeto sem instalar o pacote em si ainda
RUN uv sync --frozen --no-install-project

# Instala os navegadores do Playwright (Chromium) no Linux
RUN uv run playwright install chromium

# Copia o código do projeto
COPY ofertas/ ./ofertas/
COPY config.yaml ./

# Define variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Sao_Paulo

# Comando padrão: inicia o bot
CMD ["uv", "run", "python", "-m", "ofertas", "run"]
