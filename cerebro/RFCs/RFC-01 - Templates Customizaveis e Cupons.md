---
title: "💡 RFC-01: Templates Customizáveis e Destaque de Cupons"
aliases:
  - "RFC-01"
  - "Templates e Cupons"
tags:
  - "rfc"
  - "proposta"
  - "formatter"
  - "cupons"
date_created: 2026-09-19
status: "proposto"
---

# 💡 RFC-01: Templates Customizáveis e Destaque de Cupons

## 📋 Resumo
Atualmente, o texto das postagens do Telegram é montado por uma função estática em `formatter.py`. Esta RFC propõe a criação de um motor de templates dinâmico configurável via `config.yaml` e painel web, além de parsing e destaque inteligente para cupons de desconto.

---

## 🎯 Motivação & Benefícios
- **Personalização de Marca:** O administrador do canal pode incluir links para canais VIP, hashtags personalizadas (`#Tech`, `#Gamer`), avisos legais e rodapés customizados.
- **Aumento de Conversão em Cupons:** Cupons formatados como código monoespaçado HTML (`<code>MEUCUPOM10</code>`) permitem cópia instantânea com 1 toque no aplicativo móvel do Telegram.

---

## 📐 Especificação Técnica

### 1. Novo Campo no `models.py`
Adicionar o campo `cupom` ao dataclass `Oferta`:

```python
@dataclass
class Oferta:
    # ... campos existentes ...
    cupom: str | None = None   # Código do cupom identificado (ex: "AMAZON10", "OFF50")
```

### 2. Configuração em `config.yaml`
```yaml
template_post:
  habilitar_customizado: true
  formato: |
    🔥 <b>{titulo}</b>

    {linha_preco}
    {linha_cupom}
    {extra}

    {plataforma}
    {hashtags}
```

### 3. Extração Automática de Cupons
Criar rotina em `utils.py` com regex para identificar padrões de cupom no texto do extra e títulos:

```python
RE_CUPOM = re.compile(r"cupom\s*(?:de|:)?\s*([A-Z0-9_-]{4,20})", re.IGNORECASE)
```

### 4. Renderização do Post
Se houver cupom:
```html
🎟️ Use o cupom: <code>{cupom}</code> <i>(toque para copiar)</i>
```

---

## 🔗 Links Relacionados
- [[Bot Telegram e Postagens]] — Como as mensagens são formatadas hoje.
- [[Roadmap e Evolucao]] — Cronograma desta implementação.
