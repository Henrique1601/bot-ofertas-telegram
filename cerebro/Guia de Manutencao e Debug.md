---
title: "🛠️ Guia de Manutenção, Diagnóstico e Debug"
aliases:
  - "Troubleshooting"
  - "Debug"
  - "Manutencao"
tags:
  - "suporte"
  - "debug"
  - "manutencao"
date_created: 2026-09-19
status: "documentado"
---

# 🛠️ Guia de Manutenção, Diagnóstico e Debug

Este guia reúne os procedimentos padrão para diagnóstico rápido, comandos de manutenção e soluções para erros operacionais.

---

## 🧭 Comandos de Diagnóstico Rápido (CLI)

Execute a partir da raiz do projeto no terminal PowerShell/CMD:

```powershell
# 1. Checa pendências de configuração e integridade do ambiente
uv run python -m ofertas check

# 2. Testa a extração isolada de cada fonte (sem postar no Telegram)
uv run python -m ofertas testar ml
uv run python -m ofertas testar amazon
uv run python -m ofertas testar shopee

# 3. Testa a conversão de um link específico de produto
uv run python -m ofertas converter "https://www.mercadolivre.com.br/p/MLB123456"

# 4. Executa um único ciclo completo de busca e postagem
uv run python -m ofertas ciclo
```

---

## 🛑 Erros Comuns e Como Resolver

### 1. `Sessão do Mercado Livre expirou` ou `Linkbuilder falhou`
- **Sintoma:** O bot avisa que não conseguiu gerar links do ML.
- **Causa:** Cookies de autenticação do Mercado Livre venceram (comum a cada 30–60 dias).
- **Solução Rápida:**
  * **Opção 1 (PC Local):** Rode `uv run python -m ofertas ml-login` no seu PC (10 segundos no Chrome) e envie a pasta `data/ml_profile` para a VPS via SCP.
  * **Opção 2 (Injeção de Cookies):** Exporte os cookies do ML com a extensão Cookie-Editor e salve em `data/cookies.json` na VPS (5 segundos).
  * **Opção 3 (VNC Remoto):** Rode `./bot-ofertas-telegram/ml_login_web.sh` e abra `http://localhost:6080/vnc.html`.
  * *Veja o passo a passo completo em [[Mercado Livre#⚡ 2. Métodos de Autenticação e Login Rápido (Sem Lentidão de VNC)|Mercado Livre: Métodos de Login Rápido]].*

---

### 2. `AssociateNotEligible` na Amazon
- **Sintoma:** Aviso nos logs de que a Creators API está indisponível para a conta.
- **Causa:** A conta do Amazon Associados ainda não atingiu o volume mínimo de vendas qualificadas nos últimos 90 dias.
- **Comportamento:** O bot **não para**; ele faz o chaveamento automático para o modo Scraping com a sua tag de afiliado.

---

### 3. Bloqueio por "Smart App Control" no Windows 11
- **Sintoma:** Mensagem `Failed to spawn: python` ou erro de política do Windows.
- **Causa:** O recurso *Smart App Control* do Windows 11 bloqueia binários do Python baixados pelo `uv`.
- **Solução:**
  1. Pressione a tecla `Windows` e digite `Controle inteligente de aplicativos`.
  2. Defina como **Desativado** e reinicie o computador.

---

### 4. Telegram Recusa Imagem (`send_photo falhou`)
- **Sintoma:** Log de aviso `send_photo falhou (...), enviando como texto`.
- **Causa:** A URL da imagem do produto possui formato não suportado ou bloqueio de *hotlink*.
- **Comportamento:** O bot converte o post automaticamente para texto com botão inline sem interromper o ciclo.

---

## 🔗 Links Relacionados
- [[Arquitetura do Sistema]] — Entenda como o log é propagado.
- [[Mercado Livre]], [[Amazon]], [[Shopee]] — Especificidades de cada scraper.
- [[Configuracoes e Ambiente]] — Verificação de variáveis de ambiente.
