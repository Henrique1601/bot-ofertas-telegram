# 🚀 Guia Passo a Passo: Deploy do Bot em VPS Linux (Ubuntu / Debian)

Este guia ensina como colocar o bot para rodar 24 horas por dia em uma VPS Linux (Oracle Cloud, Hetzner, DigitalOcean, Contabo, AWS, etc.).

---

## ⚡ Método 1: Usando Docker (Recomendado e Mais Rápido)

Se você já tem o Docker instalado na sua VPS:

### 1. Enviar os arquivos para a VPS
No seu computador Windows, você pode enviar a pasta via `scp` ou clonar pelo Git:
```bash
# Exemplo via SCP (substitua pelo IP da sua VPS):
scp -r C:\caminho\para\bot-ofertas-telegram root@IP_DA_SUA_VPS:/root/bot-ofertas-telegram
```

> ⚠️ **Importante:** Se você usa o Mercado Livre, certifique-se de copiar também a pasta `data/ml_profile` gerada no seu computador para o servidor!

### 2. Acessar a VPS via SSH e iniciar o container
```bash
ssh root@IP_DA_SUA_VPS
cd /root/bot-ofertas-telegram

# Inicia o bot em background (reinicia sozinho se a VPS reiniciar)
docker compose up -d --build
```

### 3. Acompanhar os logs ao vivo
```bash
docker compose logs -f
```

### Comandos úteis do Docker:
- **Parar o bot:** `docker compose down`
- **Reiniciar o bot:** `docker compose restart`
- **Ver status:** `docker compose ps`

---

## 🛠️ Método 2: Rodando Direto no Linux (Systemd sem Docker)

Se preferir rodar nativo no sistema operacional Linux:

### 1. Entrar na pasta do projeto na VPS e rodar o instalador
```bash
cd /root/bot-ofertas-telegram
chmod +x setup_linux.sh
./setup_linux.sh
```

### 2. Testar a configuração
```bash
uv run python -m ofertas check
```

### 3. Configurar como Serviço 24/7 (Systemd)
O `systemd` garante que o bot inicie junto com o Linux e reinicie automaticamente caso ocorra alguma queda de conexão:

```bash
# Copia o arquivo de serviço para a pasta do sistema
sudo cp bot-ofertas.service /etc/systemd/system/

# Recarrega os serviços e ativa o bot para iniciar no boot
sudo systemctl daemon-reload
sudo systemctl enable bot-ofertas
sudo systemctl start bot-ofertas
```

### Comandos úteis do Systemd:
- **Ver status do bot:** `sudo systemctl status bot-ofertas`
- **Acompanhar logs ao vivo:** `sudo journalctl -u bot-ofertas -f`
- **Reiniciar o bot:** `sudo systemctl restart bot-ofertas`
- **Parar o bot:** `sudo systemctl stop bot-ofertas`

---

## 🔑 Como levar a sessão do Mercado Livre para a VPS?

Como o Mercado Livre precisa de login no navegador com 2FA, a forma mais fácil é:
1. Faça o login **uma vez no seu PC** via `uv run python -m ofertas ml-login` (ou pelo `PAINEL.bat`).
2. Copie a pasta `data/ml_profile` do seu computador para dentro da pasta `data/` na VPS:
   ```bash
   scp -r data/ml_profile root@IP_DA_SUA_VPS:/root/bot-ofertas-telegram/data/
   ```
3. O bot no Linux usará a sessão salva normalmente em modo headless!
