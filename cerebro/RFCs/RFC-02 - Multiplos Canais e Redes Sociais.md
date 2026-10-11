---
title: "💡 RFC-02: Múltiplos Canais Telegram e Cross-Posting"
aliases:
  - "RFC-02"
  - "Multiplos Canais"
tags:
  - "rfc"
  - "proposta"
  - "telegram"
  - "multicanal"
date_created: 2026-09-19
status: "proposto"
---

# 💡 RFC-02: Múltiplos Canais Telegram e Cross-Posting

## 📋 Resumo
Esta RFC propõe expandir o sistema de envio para permitir postagens simultâneas ou segmentadas em **múltiplos canais do Telegram**, grupos com tópicos e envio externo via **Webhooks do Discord** ou WhatsApp.

---

## 🎯 Motivação
- Muitos administradores possuem mais de um canal (ex: Canal Geral com todas as ofertas + Canais VIP específicos por nicho).
- Possibilidade de enviar ofertas para servidores de Discord sem esforço adicional.

---

## 📐 Especificação Técnica

### 1. Configuração de Destinos (`config.yaml`)
Substituir a dependência de um único `TELEGRAM_CHAT_ID` por uma lista flexível de canais:

```yaml
destinos:
  telegram:
    - chat_id: "-100123456789"
      nome: "Canal Geral de Promoções"
      nichos: ["todos"]
    - chat_id: "-100987654321"
      nome: "Canal VIP - Hardware & Games"
      nichos: ["tecnologia", "games"]
  
  webhooks_discord:
    - url: "https://discord.com/api/webhooks/..."
      nome: "Discord Promoções"
```

### 2. Modificação no `pipeline.py`
Iterar sobre os destinos configurados e verificar se a oferta corresponde aos nichos do canal antes de postar:

```python
async def despachar_oferta(bot: Bot, oferta: Oferta):
    for destino in config.destinos_telegram:
        if "todos" in destino.nichos or oferta.nicho in destino.nichos:
            await postar_oferta(bot, oferta, destino.chat_id)
```

---

## 🔗 Links Relacionados
- [[Bot Telegram e Postagens]] — Como o envio para o Telegram é feito atualmente.
- [[Configuracoes e Ambiente]] — Variáveis de ambiente e arquivos YAML.
- [[Roadmap e Evolucao]] — Fase de expansão multi-canal.
