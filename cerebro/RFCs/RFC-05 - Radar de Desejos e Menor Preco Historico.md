---
tipo: rfc
codigo: RFC-05
titulo: Radar de Desejos (Wishlist) e Selo de Menor Preço Histórico
status: concluido
tags:
  - rfc
  - comunidade
  - historico-precos
  - wishlist
---

# 🔔 RFC-05: Radar de Desejos e Menor Preço Histórico

## 🎯 Objetivo
Aumentar drasticamente o engajamento e a conversão de vendas através de:
1. **Radar de Desejos (Wishlist):** Inscritos do canal cadastram produtos e preços que desejam monitorar e são notificados no privado assim que o robô acha uma oferta.
2. **Selo de Menor Preço Histórico:** Comparação automática do preço atual com o histórico registrado no banco de dados SQLite (`historico_precos`), carimbando ofertas especiais com `📉 MENOR PREÇO HISTÓRICO REGISTRADO!`.
3. **Reações Interativas nos Posts:** Botões `[🔥 Valeu a pena (X)]` e `[👎 Caro (Y)]` diretamente no Telegram.

## 🛠️ Implementação
- **Banco de Dados (`ofertas/db.py`):**
  - Tabela `historico_precos (uid, preco, registrado_em)` para análise temporal.
  - Tabela `desejos (user_id, termo, preco_max, criado_em, ativo)` para wishlist.
  - Tabela `reacoes (uid, tipo, user_id)` com deduplicação de votos por usuário.
- **Bot Interativo (`ofertas/bot_interativo.py`):**
  - Comandos: `/desejo <produto> [preco]`, `/meusdesejos`, `/removerdesejo <id>`.
  - Tratamento de votos via callbacks inline (`voto:fogo:...`, `voto:caro:...`).
- **Pipeline (`ofertas/pipeline.py`):**
  - Verificação de menor preço (`db.verificar_menor_preco`).
  - Disparo de mensagens diretas no privado para os usuários com alertas compatíveis.
