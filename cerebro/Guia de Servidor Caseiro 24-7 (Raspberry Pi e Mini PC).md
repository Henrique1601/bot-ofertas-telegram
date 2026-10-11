---
title: "🍓 Guia de Servidor Caseiro 24/7 (Raspberry Pi, TV Box e Mini PC)"
aliases:
  - "Raspberry Pi"
  - "Mini PC"
  - "Servidor Caseiro"
  - "Home Server"
tags:
  - "deploy"
  - "hardware"
  - "raspberry-pi"
  - "minipc"
  - "linux"
date_created: 2026-09-21
status: "documentado"
---

# 🍓 Guia de Servidor Caseiro 24/7 (Raspberry Pi, TV Box e Mini PC)

Transformar um computador antigo, Mini PC ou placa de desenvolvimento (Raspberry Pi / Orange Pi / TV Box) em um **servidor de automação 24/7** é uma das alternativas mais econômicas e eficientes para rodar o bot de promoções.

---

## 🏆 Por que usar um Servidor Caseiro?

| Vantagem | Servidor Caseiro (Mini PC / Raspberry) | VPS na Nuvem (AWS / Oracle / Hetzner) |
| :--- | :--- | :--- |
| **Custo Mensal** | **R$ 0,00** (Zero mensalidade) | R$ 0 a R$ 35/mês |
| **Consumo de Energia** | **3W a 10W** (~R$ 2,50 a R$ 5,00/mês na conta de luz) | Não se aplica |
| **IP Residencial Real** | ✅ **100% Residencial** (quase zero chance de CAPTCHA) | ⚠️ IP de Data Center (sujeito a bloqueios da Amazon) |
| **Login no Mercado Livre** | ✅ Abre o Chrome com tela real em 1 segundo | Exige túnel SSH / VNC remoto |
| **Silencioso & Compacto** | ✅ Pode ficar escondido atrás do roteador Wi-Fi | 100% Remoto |

---

## 🖥️ Opções de Hardware Recomendadas

### 1. Raspberry Pi ou Orange Pi (ARM64)
* **Modelos:** Raspberry Pi 3B+, 4 ou 5 (ou Orange Pi Zero 3 / 3B / 5).
* **RAM Mínima:** 1 GB ou 2 GB de RAM.
* **Sistema:** **Raspberry Pi OS Lite (64-bit)** ou **Armbian (Ubuntu/Debian)**.

### 2. TV Box com processador Amlogic (Alternativa Ultrabarata: ~R$ 100 a R$ 150)
* **Modelos:** TV Boxes com chips S905W, S905X, S905X2, S905X3 (ex: TX3 Mini, Tanix TX9, X96 Max).
* **Sistema:** **Armbian Linux** gravado em cartão microSD. Consome menos de 4W.

### 3. Notebook Antigo ou Mini PC Usado (x86_64)
* **Modelos:** Notebooks com tela quebrada, Lenovo ThinkCentre Tiny, Dell OptiPlex Micro, HP ProDesk Mini (processadores Celeron, Core i3, Core i5 antigos).
* **Vantagem:** O notebook já vem com **no-break embutido (a própria bateria)**, não desligando se faltar energia rápida!
* **Sistema:** **Ubuntu Server 24.04 LTS** ou **Debian 12**.

---

## 🚀 Passo a Passo de Instalação no Linux Caseiro

### Passo 1: Instalar o sistema operacional
1. Baixe o **Raspberry Pi Imager** ou **BalenaEtcher**.
2. Grave o **Ubuntu Server 24.04 LTS (64-bit)** ou **Raspberry Pi OS Lite (64-bit)** no cartão SD / SSD.
3. Conecte o aparelho no cabo de rede do seu roteador e ligue na tomada.

---

### Passo 2: Conectar no Servidor Caseiro via SSH
No terminal do seu computador principal:

```powershell
# O usuário padrão costuma ser 'ubuntu' ou 'pi':
ssh ubuntu@IP_DO_SEU_MINI_PC
```

---

### Passo 3: Baixar e Instalar o Bot
```bash
# 1. Instalar git e dependências do Chromium
sudo apt-get update && sudo apt-get install -y git curl ca-certificates

# 2. Instalar o gerenciador rápido uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

# 3. Baixar ou transferir a pasta do bot
git clone SEU_REPOSITORIO_AQUI bot-ofertas-telegram
cd bot-ofertas-telegram

# 4. Sincronizar o ambiente e instalar o Chromium
uv sync
uv run playwright install --with-deps chromium
```

---

### Passo 4: Fazer o login do Mercado Livre
Como o Mini PC está na sua casa, se ele tiver interface gráfica ou se você rodar com navegador:
```bash
uv run python -m ofertas ml-login
```
*(Ou copie a pasta `data/ml_profile` diretamente do seu computador principal para a pasta `data/` do Mini PC).*

---

### Passo 5: Ativar para Iniciar Automaticamente no Boot (Systemd)

Crie o arquivo de serviço para o bot nunca parar:

```bash
sudo tee /etc/systemd/system/bot-ofertas.service > /dev/null << 'EOF'
[Unit]
Description=Bot de Ofertas Telegram 24/7 (Servidor Caseiro)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/bot-ofertas-telegram
ExecStart=/home/ubuntu/.local/bin/uv run python -m ofertas run
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=TZ=America/Sao_Paulo

[Install]
WantedBy=multi-user.target
EOF

# Ativa o serviço para ligar junto com o aparelho
sudo systemctl daemon-reload
sudo systemctl enable --now bot-ofertas
```

---

## 📊 Consumo de Energia e Custo Mensal Estimado

$$\text{Custo Mensal} = \left(\frac{\text{Potência (W)} \times 24\text{ horas} \times 30\text{ dias}}{1000}\right) \times \text{Tarifa kWh (ex: R\$ 0,85)}$$

* **Raspberry Pi 4 (5W):** $\approx 3,6 \text{ kWh/mês} \implies \mathbf{\approx R\$\ 3,06 \text{ por mês}}$.
* **Mini PC i3 (12W):** $\approx 8,6 \text{ kWh/mês} \implies \mathbf{\approx R\$\ 7,30 \text{ por mês}}$.

---

## 🔗 Links Relacionados
- [[Index]] — Central de navegação do Cérebro.
- [[Guia de Deploy em VPS Linux]] — Como subir na nuvem (AWS / Oracle).
- [[Configuracoes e Ambiente]] — Variáveis de ambiente e parâmetros de busca.
- [[Guia de Manutencao e Debug]] — Comandos úteis de diagnóstico e monitoramento.
