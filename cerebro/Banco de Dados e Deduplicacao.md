---
title: "🗄️ Banco de Dados e Mecanismo de Deduplicação"
aliases:
  - "Banco de Dados"
  - "SQLite"
  - "Deduplicacao"
tags:
  - "database"
  - "sqlite"
  - "deduplicacao"
date_created: 2026-09-19
status: "documentado"
---

# 🗄️ Banco de Dados e Mecanismo de Deduplicação

A persistência de histórico e controle de repetição é realizada em um banco de dados local **SQLite 3** localizado em `data/ofertas.db`.

---

## 🗂️ Estrutura da Tabela `postadas`

O banco é inicializado automaticamente na primeira execução com a seguinte DDL:

```sql
CREATE TABLE IF NOT EXISTS postadas (
    uid TEXT PRIMARY KEY,       -- Chave única '{plataforma}:{id_produto}'
    plataforma TEXT,            -- 'mercadolivre', 'shopee' ou 'amazon'
    titulo TEXT,                -- Nome do produto postado
    preco REAL,                 -- Preço registrado no momento da postagem
    postada_em TEXT             -- Data/hora ISO 8601 (ex: '2026-09-19T14:30:00')
);
```

---

## 🛡️ Lógica de Anti-Repetição (`db.ja_postada`)

Antes de autorizar uma oferta para postagem, o pipeline consulta se o `uid` foi publicado recentemente:

```python
def ja_postada(uid: str, dentro_de_dias: int) -> bool:
    with _conn() as c:
        row = c.execute("SELECT postada_em FROM postadas WHERE uid = ?", (uid,)).fetchone()
    if not row:
        return False
    postada = dt.datetime.fromisoformat(row[0])
    return (dt.datetime.now() - postada) < dt.timedelta(days=dentro_de_dias)
```

> [!tip] Comportamento da Janela Temporal
> Se um produto foi postado há 6 dias e `nao_repetir_dias: 5`, ele se torna elegível novamente para postagem caso ainda esteja com desconto excelente. Ao ser postado de novo, o `INSERT OR REPLACE` atualiza a data `postada_em` e o novo preço.

---

## 📈 Métricas e Consultas Úteis

Para inspecionar o banco diretamente via terminal ou script:

- **Total de posts históricos:**
  ```sql
  SELECT COUNT(*) FROM postadas;
  ```
- **Distribuição por plataforma:**
  ```sql
  SELECT plataforma, COUNT(*) as total, AVG(preco) as ticket_medio 
  FROM postadas 
  GROUP BY plataforma;
  ```
- **Últimas 10 ofertas postadas:**
  ```sql
  SELECT postada_em, plataforma, titulo, preco 
  FROM postadas 
  ORDER BY postada_em DESC 
  LIMIT 10;
  ```

---

## 🔗 Links Relacionados
- [[Arquitetura do Sistema]] — Onde a deduplicação se insere no pipeline.
- [[Configuracoes e Ambiente]] — Ajuste do parâmetro `nao_repetir_dias`.
