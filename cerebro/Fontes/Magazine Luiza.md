---
tipo: fonte
plataforma: Magazine Luiza / Magazine Você
status: ativo
tags:
  - fonte
  - magalu
  - magazinevoce
  - afiliados
---

# 🛍️ Magazine Luiza / Magazine Você

Módulo de captura de ofertas e conversão para links do Magazine Você (`ofertas/sources/magalu.py`).

## ⚙️ Como Funciona
- **Detecção:** Identifica links `magazineluiza.com.br`, `magazinevoce.com.br` e `magalu.com`.
- **Reescrita para Loja de Afiliado:** Reescreve qualquer link de produto do Magalu diretamente para a vitrine do seu Magazine Você (`https://www.magazinevoce.com.br/{MAGALU_LOJA}/p/{id}/`).
- **Resiliência:** Extração estruturada de título, preço de/por e imagem via Schema.org (JSON-LD) e OpenGraph.
- **Cupons:** Extrai cupons promocionais identificados na descrição do produto.
- **Busca Automática:** Coleta diária das "Ofertas do Dia" do Magazine Luiza.

## 🔑 Variáveis no `.env`
```env
MAGALU_LOJA=nome_da_sua_loja_magazine_voce
```

## 📋 Configuração no `config.yaml`
```yaml
fontes:
  magalu:
    ativa: true
```
