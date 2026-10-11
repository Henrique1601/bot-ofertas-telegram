import datetime as dt
import sqlite3

from .config import DATA_DIR
from .models import Oferta

_DB = DATA_DIR / "ofertas.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB)
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

