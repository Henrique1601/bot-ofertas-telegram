---
tipo: fonte
plataforma: AliExpress
status: ativo
tags:
  - fonte
  - aliexpress
  - afiliados
---

# 🛍️ AliExpress

Módulo de captura de ofertas e conversor de links para o AliExpress (`ofertas/sources/aliexpress.py`).

## ⚙️ Como Funciona
- **Detecção:** Identifica links `aliexpress.com`, `aliexpress.ru`, `a.aliexpress.com` e `s.click.aliexpress.com`.
- **Expansão de Links Curtos:** Resolve redirecionamentos de links do app (`a.aliexpress.com`).
- **Resiliência:** Extração de título, preço e imagens via Schema.org (JSON-LD), OpenGraph e BeautifulSoup fallback.
- **Cupons:** Extração automática de cupons anunciados na página ou colados pelo usuário.
- **Link de Afiliado:** Anexa os parâmetros `tracking_id` configurados em `.env` (`ALIEXPRESS_TRACKING_ID`).

## 🔑 Variáveis no `.env`
```env
ALIEXPRESS_TRACKING_ID=seu_tracking_id
```

## 📋 Configuração no `config.yaml`
```yaml
fontes:
  aliexpress:
    ativa: true
    buscas:
      - fone bluetooth
      - smartwatch
      - teclado mecanico
```
