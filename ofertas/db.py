import datetime as dt
import sqlite3

from .config import DATA_DIR
from .models import Oferta

_DB = DATA_DIR / "ofertas.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB)
    # Tabela principal de postagens
    c.execute(
        "CREATE TABLE IF NOT EXISTS postadas ("
        " uid TEXT PRIMARY KEY,"
        " plataforma TEXT,"
        " titulo TEXT,"
        " preco REAL,"
        " postada_em TEXT,"
        " chat_id TEXT,"
        " message_id INTEGER)"
    )
    # Migração automática caso a tabela já existisse sem as colunas novas
    cols = [col[1] for col in c.execute("PRAGMA table_info(postadas)").fetchall()]
    if "chat_id" not in cols:
        c.execute("ALTER TABLE postadas ADD COLUMN chat_id TEXT")
    if "message_id" not in cols:
        c.execute("ALTER TABLE postadas ADD COLUMN message_id INTEGER")

    # Tabela de Histórico de Preços (para detecção de menor preço histórico)
    c.execute(
        "CREATE TABLE IF NOT EXISTS historico_precos ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " uid TEXT,"
        " preco REAL,"
        " registrado_em TEXT)"
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_hist_uid ON historico_precos(uid)")

    # Tabela de Desejos / Radar de Ofertas (Wishlist dos inscritos)
    c.execute(
        "CREATE TABLE IF NOT EXISTS desejos ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " user_id INTEGER,"
        " termo TEXT,"
        " preco_max REAL,"
        " criado_em TEXT,"
        " ativo INTEGER DEFAULT 1)"
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_desejos_user ON desejos(user_id, ativo)")

    # Tabela de Reações nos posts (🔥 / 👎)
    c.execute(
        "CREATE TABLE IF NOT EXISTS reacoes ("
        " uid TEXT,"
        " tipo TEXT,"
        " user_id INTEGER,"
        " PRIMARY KEY (uid, tipo, user_id))"
    )
    return c


def ja_postada(uid: str, dentro_de_dias: int) -> bool:
    with _conn() as c:
        row = c.execute("SELECT postada_em FROM postadas WHERE uid = ?", (uid,)).fetchone()
    if not row:
        return False
    postada = dt.datetime.fromisoformat(row[0])
    return (dt.datetime.now() - postada) < dt.timedelta(days=dentro_de_dias)


def registrar(oferta: Oferta, chat_id: str | int | None = None, message_id: int | None = None) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO postadas (uid, plataforma, titulo, preco, postada_em, chat_id, message_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (oferta.uid, oferta.plataforma, oferta.titulo, oferta.preco,
             dt.datetime.now().isoformat(timespec="seconds"),
             str(chat_id) if chat_id else None,
             message_id),
        )
        if oferta.preco is not None and oferta.preco > 0:
            c.execute(
                "INSERT INTO historico_precos (uid, preco, registrado_em) VALUES (?, ?, ?)",
                (oferta.uid, oferta.preco, dt.datetime.now().isoformat(timespec="seconds")),
            )


def registrar_historico_preco(uid: str, preco: float) -> None:
    """Registra uma observação de preço para um produto."""
    with _conn() as c:
        c.execute(
            "INSERT INTO historico_precos (uid, preco, registrado_em) VALUES (?, ?, ?)",
            (uid, preco, dt.datetime.now().isoformat(timespec="seconds")),
        )


def verificar_menor_preco(uid: str, preco_atual: float, dias: int = 30) -> bool:
    """True se o preço atual for o menor já registrado nos últimos `dias` (e houve histórico anterior maior)."""
    if not preco_atual or preco_atual <= 0:
        return False
    data_limite = (dt.datetime.now() - dt.timedelta(days=dias)).isoformat()
    with _conn() as c:
        rows = c.execute(
            "SELECT preco FROM historico_precos WHERE uid = ? AND registrado_em >= ? ORDER BY registrado_em ASC",
            (uid, data_limite),
        ).fetchall()
    if not rows or len(rows) < 2:
        return False
    precos = [r[0] for r in rows if r[0] is not None]
    if not precos:
        return False
    menor_anterior = min(precos)
    maior_anterior = max(precos)
    # Tem que ser menor ou igual ao menor anterior e o histórico deve ter tido um preço significativamente maior
    return preco_atual <= menor_anterior and (maior_anterior > preco_atual * 1.05)


# ── Desejos (Wishlist de usuários) ───────────────────────────────────

def adicionar_desejo(user_id: int, termo: str, preco_max: float | None = None) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO desejos (user_id, termo, preco_max, criado_em, ativo) VALUES (?, ?, ?, ?, 1)",
            (user_id, termo.strip().lower(), preco_max, dt.datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def listar_desejos_usuario(user_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, termo, preco_max, criado_em FROM desejos WHERE user_id = ? AND ativo = 1",
            (user_id,),
        ).fetchall()
    return [{"id": r[0], "termo": r[1], "preco_max": r[2], "criado_em": r[3]} for r in rows]


def remover_desejo(id_desejo: int, user_id: int) -> bool:
    with _conn() as c:
        cur = c.execute(
            "UPDATE desejos SET ativo = 0 WHERE id = ? AND user_id = ?",
            (id_desejo, user_id),
        )
        return cur.rowcount > 0


def buscar_desejos_compativeis(oferta: Oferta) -> list[dict]:
    """Retorna lista de {user_id, termo, preco_max} interessados nesta oferta."""
    if not oferta.titulo or not oferta.preco:
        return []
    titulo_limpo = oferta.titulo.lower()
    compativeis = []
    with _conn() as c:
        rows = c.execute(
            "SELECT id, user_id, termo, preco_max FROM desejos WHERE ativo = 1"
        ).fetchall()
    for row in rows:
        did, uid, termo, pmax = row
        termos_busca = termo.split()
        if all(t in titulo_limpo for t in termos_busca):
            if pmax is None or oferta.preco <= pmax:
                compativeis.append({"id": did, "user_id": uid, "termo": termo, "preco_max": pmax})
    return compativeis


# ── Reações de Usuários (🔥 / 👎) ────────────────────────────────────

def votar_reacao(uid: str, tipo: str, user_id: int) -> tuple[int, int]:
    """Registra ou remove voto do usuário e retorna (total_fogo, total_caro)."""
    with _conn() as c:
        ja_votou = c.execute(
            "SELECT 1 FROM reacoes WHERE uid = ? AND tipo = ? AND user_id = ?",
            (uid, tipo, user_id)
        ).fetchone()
        if ja_votou:
            c.execute("DELETE FROM reacoes WHERE uid = ? AND tipo = ? AND user_id = ?", (uid, tipo, user_id))
        else:
            # Remove voto oposto se houver
            oposto = "caro" if tipo == "fogo" else "fogo"
            c.execute("DELETE FROM reacoes WHERE uid = ? AND tipo = ? AND user_id = ?", (uid, oposto, user_id))
            c.execute("INSERT OR REPLACE INTO reacoes (uid, tipo, user_id) VALUES (?, ?, ?)", (uid, tipo, user_id))

        fogo = c.execute("SELECT COUNT(*) FROM reacoes WHERE uid = ? AND tipo = 'fogo'", (uid,)).fetchone()[0]
        caro = c.execute("SELECT COUNT(*) FROM reacoes WHERE uid = ? AND tipo = 'caro'", (uid,)).fetchone()[0]
        return fogo, caro


def obter_contagem_reacoes(uid: str) -> tuple[int, int]:
    with _conn() as c:
        fogo = c.execute("SELECT COUNT(*) FROM reacoes WHERE uid = ? AND tipo = 'fogo'", (uid,)).fetchone()[0]
        caro = c.execute("SELECT COUNT(*) FROM reacoes WHERE uid = ? AND tipo = 'caro'", (uid,)).fetchone()[0]
        return fogo, caro


def obter_postada(uid: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT uid, plataforma, titulo, preco, postada_em, chat_id, message_id FROM postadas WHERE uid = ?",
            (uid,)
        ).fetchone()
    if not row:
        return None
    return {
        "uid": row[0],
        "plataforma": row[1],
        "titulo": row[2],
        "preco": row[3],
        "postada_em": row[4],
        "chat_id": row[5],
        "message_id": row[6],
    }


def total_postadas() -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM postadas").fetchone()[0]


