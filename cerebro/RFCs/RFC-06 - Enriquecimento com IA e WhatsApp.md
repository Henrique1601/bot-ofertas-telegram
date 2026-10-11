---
tipo: rfc
codigo: RFC-06
titulo: Enriquecimento com IA (Google Gemini) e Cross-Posting no WhatsApp
status: concluido
tags:
  - rfc
  - ia
  - gemini
  - whatsapp
  - cross-posting
---

# 🤖 RFC-06: Enriquecimento com IA e Cross-Posting no WhatsApp

## 🎯 Objetivo
1. **Enriquecimento por Inteligência Artificial (`ofertas/ai.py`):**
   - Limpar títulos de marketplaces cheios de palavras de spam de busca.
   - Extrair automaticamente de 2 a 3 destaques técnicos ou benefícios reais do produto.
   - Utilização do modelo Google Gemini Flash via API com fallback transparente caso a chave não esteja configurada.

2. **Cross-Posting no WhatsApp (`ofertas/whatsapp.py`):**
   - Disparo simultâneo das ofertas para grupos e canais do WhatsApp.
   - Formatação automática de legendas com markdown específico do WhatsApp (`*negrito*`, `~tachado~`, `_itálico_`).
   - Integração com Evolution API, Z-API ou gateways HTTP compatíveis.

3. **CI/CD Automatizado via GitHub Actions (`.github/workflows/deploy.yml`):**
   - Execução de testes a cada commit.
   - Deploy automático via SSH para servidores em nuvem (Oracle Cloud / VPS).
